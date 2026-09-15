# 新手上手 / Getting Started

## 1. 安装

需要 Python 3.10 或更高版本：

```bash
python -m venv .venv
python -m pip install .
```

## 2. 先做离线记忆测试

```bash
python examples/memory_only.py
```

这个示例不会连接模型服务，也不会上传数据。

## 3. 接入模型

设置 `SUPERBRAIN_LLM_BASE`、`SUPERBRAIN_LLM_KEY` 和 `SUPERBRAIN_LLM_MODEL`，然后按 `INTEGRATION.md` 使用 `SuperBrain.from_env()`。密钥只通过环境变量或外部密钥管理器提供，不要写进代码和 Git。

## 4. 选择接入方式

- Python：适合已有 Python Bot 或 Agent；
- HTTP：适合其他语言或独立进程；
- MCP：适合支持 MCP 的 Agent 客户端。

