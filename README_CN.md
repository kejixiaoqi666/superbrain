# SuperBrain 中文文档

## 它是什么

SuperBrain 是一个面向 AI 应用的 Python 基础库，提供本地记忆、上下文压缩、状态管理和 Agent 接入所需的通用组件。它适合用来构建 Telegram Bot、网页 AI、本地开发助手和自动化运维助手。

它不是大语言模型，也不是开箱即用的聊天软件。你仍需要选择模型、搭建界面或 Bot 通道，并按需接入文件、Shell、SSH、MCP 等工具。

## 架构

![SuperBrain 架构图](docs/images/architecture.svg)

消息进入后，系统先按用户和项目范围筛选记忆，再交给模型或规则处理；工具执行产生的结果和反馈可以形成候选记忆，经过接受后才进入长期召回。

## 主要能力

- **本地记忆**：SQLite 存储，按 owner、project、scope 隔离。
- **分层召回**：区分工作上下文、项目事实、决策和程序性经验。
- **重要性与反馈**：记录重要性、置信度、时间和使用反馈，帮助排序。
- **上下文预算**：在有限输入长度内优先提供相关内容。
- **状态与 checkpoint**：保存角色状态、任务阶段和可恢复进度。
- **接入契约**：为 Python、HTTP 和 MCP 提供统一调用入口。
- **可扩展适配器**：可接入模型、Telegram、SSH、OAuth、MCP 和外部 Vault。

## 一个最小示例

```python
from superbrain import SuperBrain

brain = SuperBrain()
brain.remember("这个项目使用 Python 3.12", importance=0.8)
print(brain.recall("项目使用什么语言"))
brain.close()
```

更多示例见 [`examples/`](examples/) 和 [快速开始](docs/GETTING_STARTED.md)。

## 适用场景

| 场景 | 可以解决的问题 |
| --- | --- |
| Telegram / Web Bot | 跨对话保留用户和项目上下文 |
| 本地开发助手 | 保存项目约定、任务状态和反馈 |
| 运维助手 | 保存主机别名和操作记录，凭据由独立 Vault 管理 |
| 多模型应用 | 用相同的上层调用面替换模型 Provider |

## 安全与权限边界

SuperBrain 不会自动获得系统或服务器权限。密码、Token、私钥不应写入记忆库，应由环境变量、系统密钥环或独立 Vault 管理，记忆中只保存 profile 引用。HTTP 服务默认绑定本机回环地址，公开部署前必须增加身份认证和网络隔离。

## 当前状态

已实现：核心记忆、候选到接受流程、作用域过滤、可解释召回、反馈更新、上下文预算、checkpoint、基础 HTTP/MCP 接口。

待接入或完善：真实 Telegram Gateway、OAuth 登录、SSH Executor、Secret Broker、生产级 IPC 身份认证，以及 Windows SQLite 连接清理。测试状态和限制见 [docs/STATUS.md](docs/STATUS.md)。

## 安装

```bash
pip install dist/superbrain-1.21.2-py3-none-any.whl
# 可选 MCP 支持
pip install "dist/superbrain-1.21.2-py3-none-any.whl[mcp]"
```

## 文档

- [快速开始](docs/GETTING_STARTED.md)
- [集成指南](INTEGRATION.md)
- [FAQ](docs/FAQ.md)
- [开发文档](docs/DEVELOPMENT.md)
- [安全说明](SECURITY.md)
- [MIT License](LICENSE)
