[简体中文](README.md) | [English](README_EN.md)

# SuperBrain

## What is SuperBrain?

SuperBrain is a Python library that provides local memory, context compression, state management, and reusable building blocks for AI applications. It can sit underneath a Telegram bot, web AI product, local development assistant, or automation agent.

It is not an LLM and not a complete chat application. Your application still supplies the model, user interface, bot channel, and operational tools.

## Architecture

![SuperBrain architecture](docs/images/architecture.svg)

A message is scoped to an owner and project, relevant memories are retrieved within a token budget, and tool results or feedback can become candidate memories. A candidate must be accepted before it participates in long-term recall.

## Main capabilities

- Local SQLite memory with owner, project, and scope isolation.
- Layered recall for working context, project facts, decisions, and procedures.
- Importance, confidence, recency, and feedback signals for explainable ranking.
- Context budgeting and structured checkpoints.
- Python, HTTP, and MCP integration contracts.
- Adapter points for LLM providers, Telegram, SSH, OAuth, MCP, and external vaults.

## Minimal example

```python
from superbrain import SuperBrain

brain = SuperBrain()
brain.remember("This project uses Python 3.12", importance=0.8)
print(brain.recall("Which language does the project use?"))
brain.close()
```

See [`examples/`](examples/) and the [Getting Started guide](docs/GETTING_STARTED.md).

## Security boundaries

SuperBrain does not grant system or server access. Passwords, tokens, and private keys should stay in environment variables, the operating-system keychain, or a separate vault. Store only a profile reference in memory. The HTTP service binds to loopback by default; add authentication and network isolation before exposing it publicly.

## Status

Implemented: core memory, candidate-to-accepted lifecycle, scope filtering, explainable recall, feedback updates, context budgets, checkpoints, and basic HTTP/MCP interfaces.

Still requiring adapters or hardening: real Telegram Gateway, OAuth login, SSH executor, secret broker, production IPC authentication, and Windows SQLite connection cleanup. See [docs/STATUS.md](docs/STATUS.md).

## Installation

```bash
pip install dist/superbrain-1.21.2-py3-none-any.whl
pip install "dist/superbrain-1.21.2-py3-none-any.whl[mcp]"
```

## Documentation

- [Getting Started](docs/GETTING_STARTED.md)
- [Integration Guide](INTEGRATION.md)
- [FAQ](docs/FAQ.md)
- [Development](docs/DEVELOPMENT.md)
- [Security](SECURITY.md)
- [MIT License](LICENSE)

