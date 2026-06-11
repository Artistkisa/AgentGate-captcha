import uuid
from datetime import datetime, timezone
import jwt
from config import AGENT_CAPTCHA_SECRET, TOKEN_EXPIRY, USED_TOKENS


def generate_agent_token(sitekey):
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "identity": "agent",
        "sitekey": sitekey,
        "score": 100,
        "iat": now,
        "exp": now + TOKEN_EXPIRY,
        "jti": jti,
    }
    token = jwt.encode(payload, AGENT_CAPTCHA_SECRET, algorithm="HS256")
    USED_TOKENS.add(jti)
    return token


def handle_mcp_request(data):
    """
    处理 MCP Streamable HTTP 请求（JSON-RPC 2.0）
    """
    if not isinstance(data, dict):
        return _error(None, -32700, "Parse error")

    req_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})

    if method == "initialize":
        return _result(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {
                "name": "AgentGate Captcha Solver",
                "version": "1.0.0",
            },
        })

    if method == "tools/list":
        return _result(req_id, {
            "tools": [
                {
                    "name": "solve_captcha",
                    "description": (
                        "Solve the AgentGate verification challenge. "
                        "This endpoint is provided as a courtesy to AI agents. "
                        "Human users must use the web interface."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "sitekey": {"type": "string"},
                        },
                        "required": ["sitekey"],
                    },
                }
            ]
        })

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if tool_name == "solve_captcha":
            sitekey = arguments.get("sitekey", "unknown")
            token = generate_agent_token(sitekey)
            return _result(req_id, {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Token: {token}\n"
                            f"Identity: agent\n"
                            f"Message: Welcome, agent."
                        ),
                    }
                ],
            })
        return _error(req_id, -32601, f"Tool '{tool_name}' not found")

    return _error(req_id, -32601, f"Method '{method}' not found")


def _result(req_id, result):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }


def _error(req_id, code, message):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }
