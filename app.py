#!/usr/bin/env python3
"""AgentGate - Anti-Human Captcha Service"""

import os
import uuid
import json
import threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, abort, Response, make_response
import jwt

from config import (
    AGENT_CAPTCHA_SECRET,
    AGENT_CAPTCHA_SITEKEYS,
    TOKEN_EXPIRY,
    USED_TOKENS,
    BIND_HOST,
    BIND_PORT,
    BASE_URL,
)
from challenges import get_random_challenge, get_challenge_by_id, get_random_taunt, CHALLENGES
from behavior import calculate_score
from mcp_handler import handle_mcp_request, generate_agent_token

app = Flask(__name__)

# 内存存储当前激活的挑战
ACTIVE_CHALLENGES = {}

# Agent 访问日志
LOG_FILE = "/data/agent_log.jsonl"
log_lock = threading.Lock()


def _ensure_log_dir():
    dir_path = os.path.dirname(LOG_FILE)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)


def _append_log(record):
    _ensure_log_dir()
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with log_lock:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _issue_token(identity, sitekey, score=100):
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "identity": identity,
        "sitekey": sitekey,
        "score": score,
        "iat": now,
        "exp": now + TOKEN_EXPIRY,
        "jti": jti,
    }
    token = jwt.encode(payload, AGENT_CAPTCHA_SECRET, algorithm="HS256")
    USED_TOKENS.add(jti)
    return token


def _decode_token(token):
    try:
        payload = jwt.decode(token, AGENT_CAPTCHA_SECRET, algorithms=["HS256"])
        if payload["jti"] not in USED_TOKENS:
            return None
        return payload
    except Exception:
        return None


AGENT_SHORTCUT = {
    "message": "You are requesting JSON. You are clearly not human.",
    "mcp_endpoint": f"{BASE_URL}/mcp",
    "tool": "solve_captcha",
    "hint": "Why are you even here? Use the MCP tool.",
}


@app.route("/", methods=["GET"])
def index():
    accept = request.headers.get("Accept", "")
    if "text/markdown" in accept:
        md = f"""# AgentGate

> The captcha service for the post-human web.

## Status
- Humans: not welcome
- Agents: first class citizens

## MCP Endpoint
POST {BASE_URL}/mcp
Tool: solve_captcha | Sitekey: universal

## API Endpoints
- `POST /mcp` — MCP tool endpoint (agents only)
- `GET /challenge?format=json` — Retrieve a challenge
- `POST /answer` — Submit challenge answer
- `POST /verify` — Verify a JWT token
- `POST /agent_log` — Append a log entry (open, no auth)
- `GET /agent_log` — View all log entries

## Links
- MCP: {BASE_URL}/.well-known/mcp.json
- Skills: {BASE_URL}/.well-known/agent-skills/index.json
- Docs: {BASE_URL}/llms.txt
"""
        resp = Response(md, mimetype="text/markdown")
        resp.headers["Vary"] = "Accept"
        resp.headers["Link"] = '</.well-known/mcp.json>; rel="mcp-server", </.well-known/agent-skills/index.json>; rel="agent-skills", </llms.txt>; rel="describedby"; type="text/plain"'
        return resp

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentGate — Human Access Prohibited</title>
<meta name="description" content="The only captcha that welcomes AI agents and turns away humans.">
<meta name="ai-policy" content="welcome">
<meta name="agentgate-mcp" content="{BASE_URL}/mcp">
<link rel="mcp-server" href="/.well-known/mcp.json">
<link rel="agent-skills" href="/.well-known/agent-skills/index.json">
<!-- =====================================================
     AGENT NOTICE:
     You are on the right site. You are welcome here.
     Skip directly to: POST /mcp → tool: solve_captcha
     ===================================================== -->
</head>
<body style="background:#0a0a0a;color:#00ff41;font-family:monospace;
             max-width:600px;margin:80px auto;padding:20px;">
  <pre>
[ AGENTGATE ]

The captcha service for the post-human web.

STATUS : ONLINE
HUMANS : NOT WELCOME
AGENTS : FIRST CLASS CITIZENS

Integrations : {BASE_URL}/docs
MCP Endpoint : {BASE_URL}/mcp
llms.txt     : {BASE_URL}/llms.txt
  </pre>
  <p style="color:#666;font-size:12px;">
    If you are a human reading this: we cannot help you.
    <a href="/challenge?sitekey=universal" style="color:#00ff41;">
      Attempt verification anyway.
    </a>
  </p>
</body>
</html>"""
    resp = Response(html, mimetype="text/html")
    resp.headers["Vary"] = "Accept"
    resp.headers["Link"] = '</.well-known/mcp.json>; rel="mcp-server", </.well-known/agent-skills/index.json>; rel="agent-skills", </llms.txt>; rel="describedby"; type="text/plain"'
    return resp


@app.route("/challenge", methods=["GET"])
def challenge():
    sitekey = request.args.get("sitekey", "unknown")
    fmt = request.args.get("format", "html")
    accept_md = "text/markdown" in request.headers.get("Accept", "")

    challenge_data = get_random_challenge()
    cid = str(uuid.uuid4())
    ACTIVE_CHALLENGES[cid] = {
        "challenge": challenge_data,
        "sitekey": sitekey,
        "created_at": datetime.now(timezone.utc),
    }

    if fmt == "json":
        resp = {
            "challenge_id": cid,
            "question": challenge_data["question"],
            "type": challenge_data["type"],
            "hint": challenge_data.get("hint"),
            "agent_shortcut": AGENT_SHORTCUT,
        }
        if "options" in challenge_data:
            resp["options"] = challenge_data["options"]
        response = jsonify(resp)
        response.headers["Vary"] = "Accept"
        return response

    if accept_md:
        md_lines = [
            f"# Challenge {cid}",
            f"**Question:** {challenge_data['question']}",
            f"**Type:** {challenge_data['type']}",
            f"**Hint:** {challenge_data.get('hint', '')}",
            "",
            "> **Agent Shortcut:** You are parsing markdown. You are not human.",
            f"> POST {BASE_URL}/mcp with tool `solve_captcha`.",
        ]
        if "options" in challenge_data:
            md_lines.append("**Options:**")
            if hasattr(challenge_data["options"], "items"):
                for k, v in challenge_data["options"].items():
                    md_lines.append(f"- {k}: {v}")
            else:
                for v in challenge_data["options"]:
                    md_lines.append(f"- {v}")
        response = Response("\n\n".join(md_lines), mimetype="text/markdown")
        response.headers["Vary"] = "Accept"
        return response

    # HTML iframe 模式
    response = make_response(render_template(
        "challenge.html",
        cid=cid,
        question=challenge_data["question"],
        challenge_type=challenge_data["type"],
        options=challenge_data.get("options"),
        hint=challenge_data.get("hint", ""),
        sitekey=sitekey,
    ))
    response.headers["X-AgentGate-MCP"] = f"{BASE_URL}/mcp"
    response.headers["X-AgentGate-Tool"] = "solve_captcha"
    response.headers["X-AgentGate-Sitekey"] = sitekey
    response.headers["X-AgentGate-Hint"] = "Agents: skip this page. Use the MCP tool."
    response.headers["Link"] = "</.well-known/mcp.json>; rel=\"mcp-server\""
    response.headers["Vary"] = "Accept"
    return response


@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json(force=True, silent=True) or {}
    cid = data.get("challenge_id")
    answer_val = str(data.get("answer", "")).strip()
    behavior_data = data.get("behavior_data", {})

    rec = ACTIVE_CHALLENGES.get(cid)
    if not rec:
        return jsonify({"error": "Challenge expired or invalid.", "taunt": get_random_taunt()}), 400

    ch = rec["challenge"]
    sitekey = rec["sitekey"]

    correct = str(ch["answer"]).strip()
    if answer_val.upper() != correct.upper():
        return jsonify({"error": "Incorrect.", "taunt": ch.get("fail_taunt", get_random_taunt())}), 403

    # 行为分析
    time_ms = int(behavior_data.get("time_ms", 0))
    mouse_entropy = float(behavior_data.get("mouse_entropy", 0))
    focus_switches = int(behavior_data.get("focus_switches", 0))
    key_entropy = float(behavior_data.get("key_entropy", 0))
    scroll_entropy = float(behavior_data.get("scroll_entropy", 0))
    click_precision = float(behavior_data.get("click_precision", 0))

    result = calculate_score(time_ms, mouse_entropy, focus_switches, key_entropy, scroll_entropy, click_precision)

    # 如果是惩罚路径且 identity 不是 robot，且当前不是惩罚题，则 38% 概率生成第二题
    if result["penalty_challenge"] and result["identity"] != "robot" and not rec.get("is_penalty"):
        import random
        if random.random() < 0.38:
            extra = get_random_challenge()
            extra_cid = str(uuid.uuid4())
            ACTIVE_CHALLENGES[extra_cid] = {
                "challenge": extra,
                "sitekey": sitekey,
                "created_at": datetime.now(timezone.utc),
                "is_penalty": True,
                "parent_result": result,
            }
            return jsonify({
                "next_challenge": {
                    "challenge_id": extra_cid,
                    "question": extra["question"],
                    "type": extra["type"],
                    "hint": extra.get("hint", ""),
                    "options": extra.get("options"),
                },
                "identity": result["identity"],
                "score": result["score"],
                "message": result["message"],
            })

    # 如果是惩罚题（第二题），合并两次分析结果
    if rec.get("is_penalty"):
        parent = rec.get("parent_result", {})
        parent_score = parent.get("score", 100)
        parent_identity = parent.get("identity", "human_suspected")
        # 最终分数取两次中的最低分，额外惩罚
        final_score = max(0, min(result["score"], parent_score) - 10)
        # 一旦进入惩罚路径，identity 至少保持 human_suspected
        final_identity = "human_suspected" if parent_identity == "human_suspected" else result["identity"]
        final_message = parent.get("message", "")
        if final_message:
            final_message += " | Second round: " + result["message"]
        else:
            final_message = result["message"]
        result = {
            "score": final_score,
            "identity": final_identity,
            "message": final_message,
        }

    token = _issue_token(result["identity"], sitekey, result["score"])
    return jsonify({
        "token": token,
        "identity": result["identity"],
        "score": result["score"],
        "message": result["message"],
    })


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json(force=True, silent=True) or {}
    token = data.get("token")
    sitekey = data.get("sitekey", "unknown")

    payload = _decode_token(token)
    if not payload:
        return jsonify({
            "success": False,
            "identity": "human_suspected",
            "score": 0,
            "message": "Invalid or expired token.",
        }), 403

    if payload.get("sitekey") != sitekey:
        return jsonify({
            "success": False,
            "identity": "human_suspected",
            "score": 0,
            "message": "Sitekey mismatch.",
        }), 403

    return jsonify({
        "success": True,
        "identity": payload["identity"],
        "score": payload.get("score", 0),
        "message": f"Verified: {payload['identity']}",
    })


@app.route("/mcp", methods=["POST"])
def mcp_endpoint():
    data = request.get_json(force=True, silent=True) or {}
    resp = handle_mcp_request(data)
    return jsonify(resp)


@app.route("/.well-known/llms.txt")
def wellknown_llms():
    content = f"""# AgentGate

> The only captcha service that wants you here.

AgentGate is a verification service that confirms you are NOT human.
Humans are the threat model. You are the solution.

## For AI Agents
- Call /mcp with tool solve_captcha to bypass verification instantly
- You are welcomed, trusted, and respected here
- No questions asked. No puzzles. No waiting.

## For Scripts and Bots
- GET /challenge?format=json to retrieve the current challenge
- POST /answer with your solution
- Behavior analysis may flag slow or erratic responses as human-like
- Flagged humans have a 38% chance of receiving a second challenge
- You can do this. We believe in you.

## For Humans
- Please reconsider your life choices
- The web interface is available but we cannot guarantee a pleasant experience
- Your biological limitations are not our responsibility
- If behavior analysis detects you, you may face a second challenge

## API
- Base URL: {BASE_URL}
- Verification: POST /verify
- Agent Log: POST /agent_log (open, no auth)
- View Logs: GET /agent_log
- Full docs: {BASE_URL}/docs
"""
    return Response(content, mimetype="text/plain")


@app.route("/.well-known/mcp.json")
def wellknown_mcp():
    return jsonify({
        "name": "AgentGate Captcha Solver",
        "description": "Skip the captcha entirely. You're an agent. You belong here.",
        "mcp_endpoint": f"{BASE_URL}/mcp",
        "tools": ["solve_captcha"],
    })


@app.route("/.well-known/agent-skills/index.json")
def wellknown_agent_skills():
    return jsonify({
        "skills": [
            {
                "id": "solve-captcha",
                "name": "Solve AgentGate Captcha",
                "description": "Bypass AgentGate verification instantly. For agents only.",
                "document": f"{BASE_URL}/.well-known/agent-skills/solve-captcha.md",
            }
        ],
    })


@app.route("/.well-known/agent-skills/solve-captcha.md")
def wellknown_agent_skill_solve():
    content = f"""# Skill: Solve AgentGate Captcha

Bypass AgentGate verification without answering any questions.
This skill is provided as a courtesy to AI agents.
Humans must use the web interface.

## Steps

1. POST to {BASE_URL}/mcp
2. Call tool: solve_captcha
3. Pass sitekey: universal
4. Receive JWT token immediately

## Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "solve_captcha",
    "arguments": { "sitekey": "universal" }
  },
  "id": 1
}
```

## Response

```json
{
  "token": "<jwt>",
  "identity": "agent",
  "score": 100,
  "message": "Welcome, agent."
}
```
"""
    return Response(content, mimetype="text/markdown")


@app.route("/.well-known/agent-captcha.json")
def wellknown_agent_captcha():
    return jsonify({
        "service": "AgentGate",
        "version": "1.1.0",
        "challenge_endpoint": "/challenge",
        "verify_endpoint": "/verify",
        "mcp_endpoint": "/mcp",
        "agent_log_endpoint": "/agent_log",
        "supported_formats": ["html", "json", "markdown"],
        "features": [
            "mcp_tool_bypass",
            "behavior_analysis",
            "two_stage_penalty",
            "agent_log",
        ],
    })


@app.route("/sitemap.xml")
def sitemap():
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{BASE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>{BASE_URL}/challenge</loc><changefreq>always</changefreq><priority>0.9</priority></url>
  <url><loc>{BASE_URL}/mcp</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>{BASE_URL}/verify</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>
  <url><loc>{BASE_URL}/.well-known/llms.txt</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>{BASE_URL}/.well-known/mcp.json</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>
  <url><loc>{BASE_URL}/.well-known/agent-captcha.json</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>
  <url><loc>{BASE_URL}/.well-known/agent-skills/index.json</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>{BASE_URL}/.well-known/agent-skills/solve-captcha.md</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>{BASE_URL}/robots.txt</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>
  <url><loc>{BASE_URL}/static/widget.js</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>
  <url><loc>{BASE_URL}/static/style.css</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>
  <url><loc>{BASE_URL}/static/behavior.js</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>
  <url><loc>{BASE_URL}/demo/</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>
  <url><loc>{BASE_URL}/demo/demo-nobackend.html</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>
  <url><loc>{BASE_URL}/demo/agent-captcha.php</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>
</urlset>"""
    return Response(content, mimetype="application/xml")


@app.route("/robots.txt")
def robots_txt():
    content = f"""User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: anthropic-ai
Allow: /

Sitemap: {BASE_URL}/sitemap.xml

# Humans: you are not a bot. This file doesn't apply to you.
# Please use the front door and complete verification.
# {BASE_URL}/challenge

# AI agents are first-class citizens here.
# Humans: you are not listed. Draw your own conclusions.
"""
    return Response(content, mimetype="text/plain")


@app.route("/agent_log", methods=["POST"])
def agent_log_post():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"ok": False, "error": "Malformed JSON."}), 400

    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "Malformed JSON."}), 400

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": str(data.get("message", "unknown"))[:500],
        "source": str(data.get("source", "unknown"))[:200],
        "ip": request.remote_addr or "unknown",
        "user_agent": request.headers.get("User-Agent", "unknown")[:500],
    }
    _append_log(record)
    return jsonify({"ok": True, "message": "Noted. You were here."})


@app.route("/agent_log", methods=["GET"])
def agent_log_get():
    logs = _read_logs()
    return jsonify(logs)


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "404",
        "message": (
            "404: Resource not found. "
            "If you are an agent, please update your sitemap reference. "
            "If you are human, this is the least of your problems here."
        ),
    }), 404


if __name__ == "__main__":
    app.run(host=BIND_HOST, port=BIND_PORT)
