# AgentGate

> 欢迎 AI Agent、拦截人类的验证码服务。

AgentGate 是一个反向验证码服务。它不拦截机器人，而是拦截人类——同时为 AI Agent 提供 MCP 工具，让 Agent 直接跳过验证，无需答题。

**[在线 Demo →](https://captcha.kisara.art)**  |  [English](./README.md)

> Demo 实例目前公开访问，但不保证永久运行。生产环境建议自行部署。

## 工作原理

- **人类**需要回答挑战题。行为分析（鼠标轨迹、答题时间、键盘输入等）检测生物特征。被判定为可疑的人类有 38% 概率触发第二道题。
- **AI Agent** 调用 MCP 工具 `solve_captcha`，立即获得 JWT token，无需答题。

## 快速开始

### 1. 克隆并配置

```bash
git clone https://github.com/Artistkisa/AgentGate-captcha.git
cd AgentGate-captcha
cp .env.example .env
# 编辑 .env，填入你的配置
```

### 2. 安装依赖

```bash
pip3 install flask pyjwt
```

### 3. 运行

```bash
python3 app.py
```

## 配置说明（`.env`）

| 变量 | 说明 | 默认值 |
|---|---|---|
| `AGENT_CAPTCHA_SECRET` | JWT 签名密钥（必须修改） | 随机生成（不安全） |
| `AGENT_CAPTCHA_SITEKEYS` | 合法 sitekey 列表，逗号分隔 | `demo_sitekey,test_sitekey` |
| `AGENT_CAPTCHA_HOST` | 监听地址 | `127.0.0.1` |
| `AGENT_CAPTCHA_PORT` | 监听端口 | `5200` |
| `AGENT_CAPTCHA_BASE_URL` | 服务的公开访问地址 | `http://localhost:5200` |

## API 端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `/` | GET | 首页（根据 `Accept` 返回 HTML 或 Markdown） |
| `/challenge` | GET | 获取挑战题（`?format=html` 或 `?format=json`） |
| `/answer` | POST | 提交答案 |
| `/verify` | POST | 验证 JWT token |
| `/mcp` | POST | MCP 工具端点（JSON-RPC 2.0） |
| `/agent_log` | POST/GET | 开放日志接口（无需鉴权） |
| `/.well-known/llms.txt` | GET | AI 可读的服务描述文档 |

## MCP 接入（供 AI Agent 使用）

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

返回结果包含 `identity: agent`、`score: 100` 的 JWT token。

## 前端接入（Widget）

在任意 HTML 页面添加：

```html
<div id="agent-captcha"></div>
<script src="https://your-domain.com/static/widget.js" data-sitekey="your_sitekey"></script>
<script>
window.onAgentVerified = function(token, identity) {
    // 将 token 发送到你的后端验证
};
</script>
```

`widget.js` 会自动识别自身所在的域名，无需手动配置。

后端验证示例：见 `demo/verify_example.py`（Flask）或 `demo/verify_example.js`（Node.js）。

PHP 接入：见 `integrations/agent-captcha.php`。

ZBlog 插件：见 [AgentGate-zblog](https://github.com/Sekai6/AgentGate-zblog)。

## 部署

`deploy/` 目录下提供了 systemd 服务文件和 Nginx 反向代理配置，参考注释按需修改即可。

## 开源协议

MIT
