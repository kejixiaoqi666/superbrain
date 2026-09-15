# 超脑 SuperBrain — 集成指南

超脑是一个**集成好的认知/记忆/人格板块**，其他 agent 可通过 **Python 门面库** 或 **HTTP 服务** 两种方式接入。

---

## 方式一：Python 门面库（推荐）

其他 Python agent 直接用 `SuperBrain` 门面类，一行装配全部能力。

```bash
pip install superbrain
```

```python
from superbrain import SuperBrain

# 一行装配（自动读环境变量配 LLM + 记忆库）
brain = SuperBrain.from_env()

# 或用你自己的 LLM
# brain = SuperBrain.from_llm(your_provider)

# 对话（含 认知→记忆检索→行动 全链路）
reply = brain.chat("你好，介绍一下自己")

# 写入 / 检索记忆
brain.remember("用户喜欢蓝色汽车")
hits = brain.recall("用户喜欢什么")
print(hits)  # [{"content": "...", "score": 0.9, "why": "向量+关键词"}]

# 看内在状态
state = brain.state()

# 持久化 / 恢复（一个文件 = 整个大脑）
brain.save()
brain.load()
```

### 门面接口一览

| 方法 | 作用 |
|---|---|
| `from_env()` / `from_llm(llm)` | 装配入口 |
| `chat(message)` | 完整对话 |
| `remember(content)` | 写记忆 |
| `recall(query, k)` | 检索记忆 |
| `state()` | 内在状态（需求/情绪/注意力）|
| `save()` / `load()` | 持久化 |
| `dream()` | 睡眠巩固 |
| `act()` | 主动行动 |
| `generate_thoughts()` | 自主思考（想念/关心/好奇/分享）|
| `drain_thoughts()` | 取出自主消息队列 |
| `humanize(text, person_id)` | 人性化口语化包装 |
| `search_meme(query, limit)` | 搜索表情包，返回图 URL |
| `index_concepts()` / `deduplicate()` | 记忆维护 |
| `agent` | 底层对象（高级用法）|

---

## 方式二：HTTP 服务（任何语言/agent 都可接入）

零依赖服务，用 JSON 协议调用。

```bash
# 启动（读环境变量配 LLM + 记忆库）
PORT=8090 python -m superbrain.server
```

### REST API 端点

| 端点 | 方法 | 请求 | 响应 |
|---|---|---|---|
| `/health` | GET | — | `{"status":"ok"}` |
| `/state` | GET | — | 内在状态 JSON |
| `/chat` | POST | `{"message":"..."}` | `{"reply":"..."}` |
| `/remember` | POST | `{"content":"..."}` | `{"node_id":"..."}` |
| `/recall` | POST | `{"query":"...","k":5}` | `{"hits":[...]}` |
| `/save` | POST | `{"path":"..."}` | `{"saved":"..."}` |
| `/load` | POST | `{"path":"..."}` | `{"loaded":true}` |
| `/thoughts` | POST | — | 产生自主想法 |
| `/drain_thoughts` | POST | — | 取出自主消息队列 |
| `/humanize` | POST | `{"text":"...","person_id":"..."}` | 人性化包装 |
| `/meme` | POST | `{"query":"...","limit":5}` | 搜索表情包 |
| `/tools` | POST | — | 可用工具列表 |

### 其它语言接入（curl 示例）

```bash
curl -X POST http://localhost:8090/chat -H "Content-Type: application/json" -d '{"message":"你好"}'
curl -X POST http://localhost:8090/remember -d '{"content":"用户喜欢茶"}'
curl -X POST http://localhost:8090/recall -d '{"query":"用户喜欢"}'
curl http://localhost:8090/state
```

---

## 方式三：MCP 服务（对接 Codex / Hermes）

超脑可封装成 MCP server，供 Codex / Hermes 等 MCP 客户端接入，把记忆 / 状态 / 自主关系定位 / 表达库 / 自主思考 / 表情包等"大脑能力"暴露成工具。

```bash
pip install fastmcp           # MCP 封装层依赖（核心库本身零依赖）
python -m superbrain.server_mcp          # stdio 传输
# 或 fastmcp run superbrain/server_mcp.py:mcp --transport http
```

暴露的工具（MCP 前缀 `mcp_superbrain_*`）：
`brain_chat` `memory_remember` `memory_recall` `get_state` `orientations` `expression_elements` `generate_thoughts` `drain_thoughts` `humanize` `search_meme`

**Hermes 接入**（`~/.hermes/config.yaml` 的 `mcp_servers`）：
```yaml
mcp_servers:
  superbrain:
    command: "/root/projects/superbrain/.venv/bin/python"
    args: ["-m", "superbrain.server_mcp"]
    env:
      SUPERBRAIN_LLM_BASE: "https://..."
      SUPERBRAIN_LLM_KEY: "sk-..."
      SUPERBRAIN_LLM_MODEL: "..."
      SUPERBRAIN_DB: "~/.superbrain/brain.db"
```

**Codex 接入**（`~/.codex/config.toml`）：
```toml
[mcp_servers.superbrain]
command = "/root/projects/superbrain/.venv/bin/python"
args = ["-m", "superbrain.server_mcp"]
env = { SUPERBRAIN_LLM_BASE = "https://...", SUPERBRAIN_LLM_KEY = "sk-...", SUPERBRAIN_LLM_MODEL = "..." }
```

注：不配 LLM 时，记忆 / 状态 / 关系 / 表达库 / 自主思考 / 表情包等核心能力仍可用；对话（`brain_chat`）由外层 agent 用自己的 LLM + 超脑记忆状态组织。

---

## 环境变量

| 变量 | 用途 |
|---|---|
| `SUPERBRAIN_LLM_BASE` | LLM API 地址 |
| `SUPERBRAIN_LLM_KEY` | LLM 密钥 |
| `SUPERBRAIN_LLM_MODEL` | 模型名 |
| `SUPERBRAIN_DB` | 记忆库路径（默认 `~/.superbrain/brain.db`）|
| `PORT` / `HOST` | 服务端口/地址 |

---

## 接入示例（喂给其它 agent）

### 对话 agent
```python
brain = SuperBrain.from_env()
brain.remember("用户偏好简洁回答")
reply = brain.chat("我有什么偏好")  # 会自动检索到上面那条记忆
```

### 记忆服务（给无记忆的 agent）
```python
hits = brain.recall(incoming_query, k=3)
context = "\n".join(h["content"] for h in hits)
# context 注入你的 prompt，处理完再 remember() 沉淀
```

### 认知状态（给需要"内在状态"的 agent）
```python
s = brain.state()  # {"needs":..., "emotion":..., "attention":...}
```

---

## 推荐用法
- **同机 / Python agent** → 门面库（快、直接）
- **跨语言 / 远程 / 独立服务** → HTTP 服务

两者共享同一大脑（同一持久化文件），可混用。