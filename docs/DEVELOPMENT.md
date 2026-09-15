# 超脑 SuperBrain 开发文档

源码开发约定、测试发布流程、已知坑。这是项目自己的文档（与 Hermes 完全隔离）。

## 工程约定

1. **零依赖**：只用标准库。统计用 `statistics`，随机用 `random`，哈希用 `hashlib.blake2b`（**绝不用内置 `hash()`，进程级随机化**）。
2. **内容冻结**：记忆节点的 content 永不改写，用 supersede 边表达取代。
3. **FTS5 用 `tokenize='trigram'`**：默认 tokenizer 对中文失效，trigram 才支持中文。
4. **持久化覆盖全部状态**：认知+人格+会话全序列化进 store 的 meta 表，save/load 漏了就重启失忆。
5. **每改一个模块**：同步补 `to_dict`/`from_dict` + `save`/`load` 传参 + 测试。

## 测试与发布

```bash
cd /root/projects/superbrain
python -m venv .venv && source .venv/bin/activate
pip install -e .                      # 开发安装
python -m unittest discover -s tests   # 跑测试
python -m build --wheel               # 构建 wheel 到 dist/
```

## 架构速查

```
src/superbrain/core/
├── agent.py          # 主循环入口（SuperBrainAgent）
├── llm.py            # LLM Provider + from_env + estimate_tokens
├── gwt.py goals.py planner.py scheduler.py state.py tools.py learning.py
├── cognition/        # needs emotion self_tune neurochem metacognition
├── personality/      # identity seed values relationship self_model
└── memory/           # node store retrieval heat embeddings distill dream
                      # concept dedupe working eventlog time_sense pisa
```

## 已知坑

- FTS5 默认 tokenizer 中文查不到 → trigram
- deepseek 推理模型 reasoning 占满 max_tokens 致 content 空 → 抽取类 max_tokens=2000
- `hash()` 进程级随机 → 嵌入必须 blake2b
- 情绪扩展维度（certainty/safety/fatigue/attachment）save/load 漏恢复会失忆
- 会话态（对话/摘要/工作记忆/事件日志）也要持久化，否则重启丢最近上下文

## 与 Hermes 的关系

**完全隔离**。超脑是独立核心库，尚未与 Hermes 融合。两者互不依赖，各自独立运作。
