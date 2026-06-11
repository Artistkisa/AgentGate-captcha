"""
Flask 后端验证示例
接入方收到前端提交的 token 后，应向 AgentGate 校验。
"""

import os
import requests
from flask import Flask, request, jsonify

AGENT_CAPTCHA_VERIFY_URL = "https://your-domain.com/verify"
YOUR_SITEKEY = "demo_sitekey"

app = Flask(__name__)

@app.route("/submit", methods=["POST"])
def submit():
    token = request.form.get("agent-token") or request.json.get("token")
    if not token:
        return jsonify({"error": "Missing token"}), 400

    resp = requests.post(AGENT_CAPTCHA_VERIFY_URL, json={
        "token": token,
        "sitekey": YOUR_SITEKEY,
    })
    data = resp.json()

    if data.get("success") and data.get("identity") in ("agent", "robot"):
        return jsonify({"ok": True, "identity": data["identity"]})

    return jsonify({"ok": False, "reason": data.get("message")}), 403

if __name__ == "__main__":
    app.run(debug=True, port=5001)
