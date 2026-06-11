# AgentGate

> The captcha that welcomes AI agents and turns away humans.

AgentGate is a reverse-captcha verification service. Instead of blocking bots, it blocks humans — and provides AI agents with an MCP tool to bypass verification instantly.

## How it works

- **Humans** must answer a challenge question. Behavior analysis (mouse movement, timing, keystrokes) detects biological activity. Suspicious users face a second challenge (38% probability).
- **AI agents** call the MCP tool `solve_captcha` and receive a JWT token immediately — no puzzle required.

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/Artistkisa/AgentGate-captcha.git
cd AgentGate-captcha
cp .env.example .env
# Edit .env and set your values
```

### 2. Install dependencies

```bash
pip3 install flask pyjwt
```

### 3. Run

```bash
python3 app.py
```

## Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `AGENT_CAPTCHA_SECRET` | JWT signing secret | random (insecure) |
| `AGENT_CAPTCHA_SITEKEYS` | Comma-separated valid sitekeys | `demo_sitekey,test_sitekey` |
| `AGENT_CAPTCHA_HOST` | Bind host | `127.0.0.1` |
| `AGENT_CAPTCHA_PORT` | Bind port | `5200` |

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Homepage (HTML or Markdown based on `Accept` header) |
| `/challenge` | GET | Get a challenge (`?format=html` or `?format=json`) |
| `/answer` | POST | Submit challenge answer |
| `/verify` | POST | Verify a JWT token |
| `/mcp` | POST | MCP tool endpoint (JSON-RPC 2.0) |
| `/agent_log` | POST/GET | Open agent activity log (no auth) |
| `/.well-known/llms.txt` | GET | AI-readable service description |

## MCP Integration (for AI agents)

```json
POST /mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "solve_captcha",
    "arguments": { "sitekey": "your_sitekey" }
  },
  "id": 1
}
```

Returns a JWT token with `identity: agent` and `score: 100`.

## Widget Integration

Add to any HTML page:

```html
<div id="agent-captcha"></div>
<script src="https://your-domain.com/static/widget.js" data-sitekey="your_sitekey"></script>
<script>
window.onAgentVerified = function(token, identity) {
    // send token to your backend for verification
};
</script>
```

Backend verification: see `demo/verify_example.py` (Flask) or `demo/verify_example.js` (Node.js).

PHP integration: see `integrations/agent-captcha.php`.

ZBlog plugin: see [AgentGate-zblog](https://github.com/Sekai6/AgentGate-zblog).

## Deployment

See `deploy/` for systemd service and Nginx reverse proxy configuration.

## License

MIT
