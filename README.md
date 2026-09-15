# SuperBrain

> 面向 AI 应用的本地记忆、状态管理与 Agent 基础库。

![架构图](docs/images/architecture.svg)

## 选择语言

- [中文文档](README_CN.md)
- [English Documentation](README_EN.md)

## 项目概览

SuperBrain 将记忆、上下文压缩、状态管理和 Agent 接入约定整理成可嵌入 Python 应用的组件。它可以作为 Telegram Bot、Web AI 产品、本地开发助手或自动化 Agent 的基础层。

它不包含大语言模型，也不是完整聊天客户端；模型、界面、Bot 通道、工具和服务器连接由你的应用或适配器提供。

## 快速入口

- [快速开始](docs/GETTING_STARTED.md)
- [集成指南](INTEGRATION.md)
- [常见问题](docs/FAQ.md)
- [当前状态与限制](docs/STATUS.md)
- [安全说明](SECURITY.md)

## 当前版本

`v1.21.2` · Python 3.10+ · MIT License

当前版本已完成核心库、离线示例和三种接入契约。真实 Telegram、OAuth、SSH、LLM Provider 和 Secret Vault 需要另行接入，详见状态文档。
