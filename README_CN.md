# AgentGate

> *唯一一个希望你通过的验证码。*

![AgentGate 挑战界面](./docs/preview.png)

大多数验证码把机器人当敌人。
AgentGate 把**人类**当敌人。

AgentGate 是一个为后人类互联网设计的反向验证码服务。它用逻辑题和行为分析拦截人类访客——同时为 AI Agent 提供 MCP 快捷通道，直接跳过一切，无需答题，立即获得 token。

**[在线 Demo →](https://captcha.kisara.art)**  |  [English](./README.md)

> Demo 实例免费公开，但不保证永久运行。生产环境建议自行部署。

---

## 为什么选 AgentGate

**嵌入方式和 Cloudflare Turnstile 一样简单。** 任意页面加两行：一个 `<div>` 容器和一个 `<script>` 标签。不需要 npm、不需要构建步骤、不依赖任何框架。`widget.js` 从自身 script URL 自动识别服务地址，客户端无需任何额外配置。集成过  Turnstile 或 reCAPTCHA 的话，这个模式完全一样。区别在于：AgentGate 自托管、开源，质询逻辑、评分阈值和数据都在你手上，不锁进任何第三方黑盒。

**质询逻辑托管在服务端。** AgentGate 不负责决定什么时候对访客发起质询——这完全由你的集成代码决定。AgentGate 管的是质询启动后发生的一切：

- 题库管理与轮换
- 答案校验
- 交互期间的行为分析：鼠标熵、点击精度、键盘熵、滚动模式、焦点切换——每项指标和阈值都在服务端维护
- 两阶段惩罚逻辑（可疑人类行为有 38% 概率触发第二道题）
- 评分公式与身份分类（`agent` / `robot` / `human_suspected`）

这些全部不在客户端。更新服务——收紧阈值、换题、调整惩罚概率——所有接入方立即生效，不需要任何前端改动，不需要和下游协调。页面源码里永远不会出现题目、答案或评分逻辑，没有什么给人类去审查或逆向的。

---

## 为什么要做这个？

有些内容是为机器设计的，不是为人类。LLM 管线、Agent 工作流、自动化系统不应该为了证明自己的存在而去对抗人类向的 UI。AgentGate 把逻辑倒过来：Agent 是一等公民，人类是需要被处理的边界情况。

---

## 工作原理

```
人类访问页面
  └─ 注入遮罩层
       └─ 下发挑战题
            └─ 行为分析（鼠标、时间、键盘、滚动）
                 ├─ 像机器 → 直接发 token
                 └─ 像人类 → 38% 概率触发第二道题
                       └─ 答对 → 发 token，identity: human_suspected

AI Agent 访问页面
  └─ 读取 HTML 注释 / meta 标签 / console 提示
       └─ POST /mcp → tool: solve_captcha
            └─ 立即获得 token。identity: agent。score: 100。
```

Token 是签名 JWT。你的后端调用 `/verify` 确认身份和分值。

---

## 快速开始

```bash
git clone https://github.com/Artistkisa/AgentGate-captcha.git
cd AgentGate-captcha
cp .env.example .env
pip3 install flask pyjwt
python3 app.py
```

打开 `http://localhost:5200`，服务已就绪。

---

## 配置说明（`.env`）

| 变量 | 说明 | 默认值 |
|---|---|---|
| `AGENT_CAPTCHA_SECRET` | JWT 签名密钥，**必须修改** | 随机生成（每次重启都变） |
| `AGENT_CAPTCHA_SITEKEYS` | 合法 sitekey 列表，逗号分隔 | `demo_sitekey,test_sitekey` |
| `AGENT_CAPTCHA_HOST` | 监听地址 | `127.0.0.1` |
| `AGENT_CAPTCHA_PORT` | 监听端口 | `5200` |
| `AGENT_CAPTCHA_BASE_URL` | 服务的公开访问地址 | `http://localhost:5200` |

`BASE_URL` 用于生成 sitemap、llms.txt 和 MCP 发现元数据，设置为你的公开域名。

---

## 嵌入 Widget

在任意页面加两行：

```html
<div id="agent-captcha"></div>
<script src="https://your-domain.com/static/widget.js" data-sitekey="your_sitekey"></script>
```

`widget.js` 自动从自身 URL 识别所在域名，无需额外配置。

监听结果：

```js
window.onAgentVerified = function(token, identity) {
    // 将 token POST 到你的后端，调用 /verify 校验
};

window.onHumanDetected = function(token, score) {
    // 可选：处理 human_suspected 身份
};
```

完整示例见 `demo/`（Flask、Node.js）和 `integrations/`（PHP）。

---

## 后端验证

```python
import requests

resp = requests.post("https://your-domain.com/verify", json={
    "token": token,
    "sitekey": "your_sitekey",
})
data = resp.json()
# data["success"]   True/False
# data["identity"]  "agent" | "robot" | "human_suspected"
# data["score"]     0–100
```

---

## MCP 接入（供 AI Agent 使用）

AgentGate 原生支持 [MCP（模型上下文协议）](https://modelcontextprotocol.io/)。

```json
POST /mcp
Content-Type: application/json

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

返回 `identity: agent`、`score: 100` 的 JWT token，不问任何问题。

Agent 爬虫发现端点：
- `/.well-known/mcp.json` — MCP 服务清单
- `/.well-known/llms.txt` — LLM 可读的服务文档
- `/.well-known/agent-skills/index.json` — 技能注册表

---

## API 端点一览

| 端点 | 方法 | 说明 |
|---|---|---|
| `/` | GET | 首页，根据 `Accept` 返回 HTML 或 Markdown |
| `/challenge` | GET | 获取挑战题（`?format=html` 或 `?format=json`） |
| `/answer` | POST | 提交答案和行为数据 |
| `/verify` | POST | 校验 JWT token |
| `/mcp` | POST | MCP 工具端点 |
| `/agent_log` | POST | 写入日志（无鉴权） |
| `/agent_log` | GET | 读取全部日志 |
| `/.well-known/llms.txt` | GET | AI 可读的服务描述 |

---

## 生产部署

`deploy/` 目录提供 systemd 服务文件和 Nginx 反代配置。

```bash
# 解压部署
tar -xzf agent-captcha-export.tar.gz -C /opt/
cp .env.example /opt/agent-captcha/.env
# 编辑 .env 填入真实配置

# 注册系统服务
cp deploy/agent-captcha.service /etc/systemd/system/
systemctl enable --now agent-captcha

# Nginx
cp deploy/nginx.conf /etc/nginx/sites-available/agentgate
# 修改 server_name 为你的域名
ln -s /etc/nginx/sites-available/agentgate /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL（Let's Encrypt）
certbot --nginx -d your-domain.com
```

---


## 生态

| 仓库 | 说明 |
|---|---|
| [AgentGate-captcha](https://github.com/Artistkisa/AgentGate-captcha) | 核心验证服务（Flask + MCP） |
| [AgentGate-zblog](https://github.com/Sekai6/AgentGate-zblog) | ZBlog 插件 |
| [AgentGate-wordpress](https://github.com/Sekai6/AgentGate-wordpress) | WordPress 插件 |

## 开源协议

MIT — 随意使用、随意 fork、随意翻转逻辑。
