# 超脑 SuperBrain —— 开发交接文档

> 本文件供新会话无缝接续，记录当前状态和下一步计划。

## 当前状态（v1.21.2）

- 源码 `/root/projects/superbrain`，纯 Python 零依赖，**203 测试全过**
- 生命周期感板块三块已完成：自主思考 / 人性化 / 表情包工具（v1.18.0 新增）
- **v1.21.2 体量/性能/稳定性极限优化**：
  - 体量：7 处无限增长结构改 deque 上限（emotion._need_history=100/_reward_history=200、attention.history=50/_novelty_seen=2000、metacognition._reflections=100、self_tune.fitness_history=50、Relationship.notes=200）——长期运行内存不再无限增长
  - 性能：3000 轮长会话基准，内存稳定 2.2MB、峰值 2.4MB，各列表长度被上限控制
  - 稳定性：反复 save/load 20 次一致、close 幂等、autopilot 50 次启停无线程泄漏、并发 5w 条队列不丢
  - 修复：attention._novelty_seen 裁剪 bug（deque(maxlen) 自动裁剪不同步 seen 致无限增长）
- **v1.20.0 自主关系定位** / **v1.20.1 底层表达元素库** / **v1.21.0 MCP 对接层（对接 Codex/Hermes）**
- **v1.21.1 全量暴力测试加固**：跨功能组合(chat×humanize_output×person_id×关系×自主思考×表达库)+持久化往返+状态一致性，修复 3 类真实 bug：
  - expression_library 对脏 orientation(list/dict) 崩溃 → 类型防御
  - recall 的 k 非 int 切片崩 → 类型防御
  - autonomous.enqueue 无类型防御(非 dataclass 入队致 to_dict 崩) → 仅接受 AutonomousThought
- **v1.21.0 MCP 对接层（对接 Codex / Hermes）**：`server_mcp.py` 用 FastMCP 把超脑核心能力封装成 10 个 MCP 工具（brain_chat/memory_* /get_state/orientations/expression_elements/generate_thoughts/drain_thoughts/humanize/search_meme）。stdio 握手 + 工具发现 + 调用验证通过；无 LLM 时核心大脑能力仍可用（stub 降级）。`pip install superbrain[mcp]` 装依赖。接入方式见 INTEGRATION.md
- 版本演进：v1.18.x(三块)→ v1.19.x(人性化接入 chat + 修复)→ v1.20.x(自主关系定位 + 表达元素库)→ v1.21.0(MCP 对接层)
- 已交付**集成板块**双入口：
  - `SuperBrain` 门面库（`from superbrain import SuperBrain; brain = SuperBrain.from_env()`）
  - `server` HTTP 服务（`python -m superbrain.server`，端口 8090）
- 交付产物：`/root/projects/superbrain-dist/superbrain-v1.18.0-src.tar.gz` + `dist/*.whl`
- 文档：`INTEGRATION.md`（接入指南）、`docs/DEVELOPMENT.md`（开发约定）

## 完整能力清单（已实现，勿重复）

**认知层**（5模块）：PSI五大需求 + 情绪梯度(内部≠对外) + 神经化学 + 元认知(EG-MRSI) + 自调参
**记忆层**（24模块）：四类记忆 + 四路检索 + RRF + 遗忘曲线 + 内容冻结 + 概念图 + PISA + 时间体感 + 事件日志 + 13个巩固/自进化机制
**人格层**（5模块）：身份 + 种子 + 价值观 + 关系 + 自我模型 + 多尺度表达
**架构**：GWT全局工作空间 + 注意力引擎 + 目标系统 + LLM规划 + function-calling + 滚动摘要 + 自动保存 + 原子写 + 上下文清洗

**★ 生命感板块（v1.18.0 新增，三块全落地）**
1. **自主思考** `core/autonomous.py`：`AutonomousThoughtEngine` 基于内在状态主动产生想法（想念=关系久未互动、关心=对方近期情绪低落note、好奇=CERTAINTY需求高、分享=RELATEDNESS需求高），非随机非被动；事件去重 + 冷却(quiet_hours) + 自主消息队列(enqueue/drain)，to_dict/from_dict 持久化。
2. **人性化对话** `core/humanize.py`：`HumanizeEngine` 结合情绪(valence/arousal)+关系亲密度+昵称生成卖萌("喵""啦""嗷")、亲昵("哎哎哎""贴贴""昵称~")、情绪化("嘿嘿""呜呜")口语表达，纯规则零依赖。
3. **表情包工具** `core/meme_tool.py`：`search_meme`(urllib 调 memegen.link，失败降级到内置 twemoji 索引)+ `register_meme_tool` 注册 `search_meme` 工具(media/read)。

## 生命感板块集成接口（v1.18.0）

门面 `SuperBrain` 新增：
- `generate_thoughts()` → 基于内在状态产生 `[AutonomousThought]`（同时进队列）
- `drain_thoughts()` → 取出自主消息队列（供上层定时拉取灌进对话）
- `humanize(text, person_id=None)` → 按情绪+与person亲密度/昵称包装口语化
- `search_meme(query, limit=5)` → 返回 `[{url, title, source}]`

agent 层：`_agent.autonomous` / `_agent.humanize` / 工具注册表有 `search_meme`；`enable_autopilot(dream, act, thought_interval=900)` 新增 thought 周期，空闲产生自主想法。

HTTP 新增端点：`POST /thoughts`、`POST /drain_thoughts`、`POST /humanize`、`POST /meme`。

**典型用法（上层 agent 让它"有生命感"）**：
```
brain.generate_thoughts()      # 定时/空闲触发一次，产生想法的同时入队
msgs = brain.drain_thoughts()  # 取出待发消息
for m in msgs:
    text = brain.humanize(m.content, person_id=user_id)  # 包装口语化
    send_that(text)            # 上层 agent 把它发出；需要图时调 brain.search_meme(...)
```

## 团队协作模式（延续使用）

- DS(主脑) 下命令统筹 + GPT-6-astra(中成熙 zcx) 开发 + DS 独立复核（绝不盲信）
- 本轮 DS 复核抓到并修复子代理 4 处隐蔽缺陷：meme 工具 handler 签名与 `Tool.call(**kwargs)` 不匹配(集成必崩)、自主思考逐字遍历中文触发词(宽匹配)、certainty 判断死代码、scheduler 首次立即触发导致 autopilot 与 close 竞态 segfault。详见 skill:subagent-orchestration
- 详见 skill:subagent-orchestration

## 环境

- 主力 deepseek-v4-pro(dpdns)，回退 [flash(dpdns), MiniMax-M3(hzjingmu)]，api_max_retries=2
- delegation = zcx gpt-6-astra
- 测试命令：`cd /root/projects/superbrain && .venv/bin/python -m unittest discover -s tests`（170 个）
- 构建：`.venv/bin/python -m build --wheel`；src 包用 `tar czf` 打包 src/

## 下一步计划（用户可继续补充）

生命感三块已交付，可做的后续（非承诺）：
1. 把自主思考接入上层 agent 的无人值守 cron：定时 `drain_thoughts`，有想法才唤醒发消息（静默巡检模式）
2. 表情包工具扩充真实在线源（当前 memegen+twemoji 兜底），接入后返回的图直接发给用户
3. 人性化与人格层做更细的"长期个性一致性"绑定（如持续卖萌偏好记忆）