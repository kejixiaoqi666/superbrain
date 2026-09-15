# 超脑 SuperBrain —— 开发交接文档

> 本文件供新会话无缝接续，记录当前状态和下一步计划。

## 当前状态（v1.0.0 — 对外正式 Release）

- **v1.0.0 = 纯 Python 实现的最终 release（对外 Release 1.0.0）**，作为发布的第一版正式包；后续将接入 Rust 混合内核做强开发（PyO3 + HNSW/SIMD/BM25）。
- 源码 `/root/projects/superbrain`，纯 Python 零依赖，**349 测试全过**（pyflakes src 全量 0 告警）
- **v2.0.0 漏洞挖掘(第3轮)+行为回路**：挖漏洞抓修 2 个 save/load 往返 bug——① `load_state`/`load_state_from_store` 对合法但非 dict 的 JSON(如字符串)崩 AttributeError → 加 isinstance 防御；② `_restore` 只恢复 personality._traits，丢 autonomy_mode/custom_style(往返后回到 autonomous/空) → 补恢复。安全扫描确认无 Medium/High 可利用漏洞(命令执行有批准门禁、SQL 无注入)，并发 TypeError 为单实例单线程边界、超限输入不崩。补**③愧疚→修复关系回路**：`autonomous` 加 `ThoughtType.REPAIR`，愧疚≥0.4 时对最在意的人生出"想道歉/补偿"冲动；**②情绪偏置决策**：低落(<-0.3)抑制好奇探索、倾向"稳住眼前"(保守)。固化 test_state(2回归)+test_emotion_mechanisms(TestSocialMotivation 4测试)
- **v2.0.0 内部机制②③④落地**：**②认知-情绪回路**——`agent.recall` 情绪一致性记忆提取：以心境(mood)为一致性信号，低落偏向想起负面、高涨偏向正面，不一致的轻微抑制(×0.5)；**③社会情绪**——`EmotionGradient.social_update(pride/guilt)` 自豪(做成/帮到人→valence+dominance上行) / 愧疚(失责/伤害关系→下行且驱动修复)，接进 `agent.chat()`(成功→自豪、对重要的人失败→愧疚)；**④需求动力学**——`NeedDriveSystem._learn_importance()` 相对持续高缺口的 need 重要性习得上升(形成个性偏好，0.5..2.0有界)。固化 `tests/test_emotion_mechanisms.py`（自豪/愧疚/自豪消愧/需求习得有界/情绪一致符号与抑制）
- **v2.0.0 情绪动力学加深（内部机制 50%→ 提升）**：EmotionGradient 从"点状态计算"升级为"动力学系统"——① **心境(mood)慢变量**：`EmotionalState.mood` 随瞬时情绪长期累积缓慢漂移(乐观/悲观基线)；② **情绪时间衰减** `elapse(dt,tau)`：瞬时情绪按指数曲线向心境基线回归("事件会过去，心境底色还在")，接进 `dream()` 睡眠=时间流逝；③ **情绪感染** `update(contagion)`：与重要且长期低落的人相处时自身情绪被牵引(共情传染)，接进 `agent.chat()`(按用户画像 mood_mean × 熟悉度)。固化 `tests/test_emotion_mechanisms.py`（mood漂移/时间衰减回归/快慢分离/正负感染/零感染）
- **v2.0.0 Release 迁移修复**：安装验收抓到两个真实旧库兼容 bug——① 旧版 brain.db 缺新列时 `CREATE TABLE IF NOT EXISTS` 不加列，导致 `no such column: scope` 崩溃 → 加 `MemoryStore._migrate_schema()` 自动 ALTER 补列(scope/tier/valence/retention 等)；② 旧数据 tags 为 NULL 时 `json.loads` 崩溃 → 加 `_parse_tags()` 容错。均用真实旧库验收通过（补列/保留数据/可写可查）。固化 `tests/test_forgetting.py::TestSchemaMigration`。
- **v1.22.1 记忆库物理上限 + 对话浓缩**：`MemoryStore.max_db_bytes`(默认1GB,可配) + `db_size()/over_size_limit()` 护栏。`agent.dream()` 自动调 `_condense_session_memories()`——把超过保留窗口(默认30天)的旧 session 对话记忆浓缩成**一条 user 常青要点记忆**(LLM 提炼，无 LLM 退化启发式)，原始细节降级 archival(**不一句话记一句、30天后细节遗忘、保留重点关键**)；库超 1GB 时强制更激进浓缩。另修复 `agent.py` 缺 `import time` 的静默 NameError 隐患。固化 `tests/test_condense.py`（LLM浓缩/启发式退化/不足批次跳过/DB上限）
- **v1.22.1 遗忘-重激活闭环**：修复「一年对话记忆无限增长」隐患——Consolidator 此前是 opt-in 从未被自动调用。现 `agent.dream()` 自动调 `_forget_memory()`，把长期未访问的低价值 recall 记忆降级 archival（**遗忘≠删除**，物理不删，只是脱离活跃召回）；`store.search` 命中 archival 记忆时自动 `promote` 回 recall（**提起来又活跃**）。弱相关想不起、强相关提起即重激活。物理增长靠 FTS5 候选路径保证检索不退化。固化 `tests/test_forgetting.py`（降级/弱相关不召回/强相关重激活/活跃不误降）
- **v1.22.1 长会话有界性固化**：压测验证 2000 轮对话内存峰值仅 1.0MB，`_conversation`(token 预算制压缩)停在 20 条而非无界增长、各有界结构(need/reward/attn/meta)全部在硬上限内；固化为 `test_stability.py` 回归测试（`TestLongSessionBounded`，300 轮 + 结构上限）
- **v1.22.1 覆盖+诊断加固**：补 `tests/test_server.py` HTTP 服务测试（server.py 覆盖率 59%→72%，10 端点测试）+ `tests/test_server_mcp.py` 对接层测试（server_mcp.py 覆盖率 0%→81%，5 测试）+ `tests/test_llm.py` 通道层测试（llm.py 覆盖率 56%→100%，10 测试）；scheduler 后台任务异常补 `logger.warning`（不再静默，持续失败可诊断）、planner LLM 降级补 `logger.debug`；确认 `memory_remember` 经 facade 返回 str 本就兼容（撤销误改）
- **v1.22.1 健壮性加固**：修复 `add_many` 未导入 Iterable(NameError 隐患)、`adaptive_search` 多粒度分支半成品死逻辑(weights 算了没用→已实现真加权熵路由)、`_maybe_compress` LLM 不可用时 `_conversation` 无界增长隐患(改 finally 降级截断)、`set_personality/apply_style/set_user_style` 脏输入崩溃(加 isinstance 防御)；autoflake 清理 40+ 处未使用 import，pyflakes 归零
- 生命周期感板块三块已完成：自主思考 / 人性化 / 表情包工具（v1.18.0 新增）
- **v1.22.0 三框架能力（内核只做框架不做设定的哲学延续）**：
  1. **人格维度显式化** `core/personality/dimensions.py`：大五中性骨架，初值全中性(0.5)/把握度0，人格从经历/用户反馈「长出来」非预设。`observe()`被动渐近成长(有界移动+饱和) + `set()`显式设定；`profile_text()`注入prompt只列显著维度
  2. **自主目标生成** `core/autonomous_goals.py`：从需求/情绪/关系/人格维度涌现中长期「意图」(区别于即时任务)，跨会话存活，冷却去重；autopilot tick 空闲自动生成
  3. **被动用户画像** `core/user_profile.py`：零LLM启发式被动观测(沟通风格/情绪基调/话题频率)，明确偏好/兴趣来自学习信号，带把握度、有界、可溯源
- **v1.22.1 自主目标闭环**：`Goal.source/source_id` + `GoalManager.adopt_autonomous()/has_source()` 去重采纳；`act()` 优先推进自主目标（意图→目标→行动闭环），无自主目标才即时派生需求目标；`facade.adopt_goals()` 透传
- **v1.22.1 人格/画像驱动表达**：`HumanizeEngine.humanize()` 新增 `personality`/`user_profile` 参数——高宜人性→亲昵门槛降低(温柔)、高神经质→情绪低落阈值放宽(更情绪化)、高外向性→卖萌概率上调(活泼)、用户画像情绪基调低落→追加关心("你要好好的")；`facade.humanize()` 自动传入当前人格维度与该用户画像
- **v1.22.1 人格维度被动成长**：`PersonalityDimensions.observe_interaction(text)` 从相处经历自动 observe 人格——用户探索→开放性↑、体贴→宜人性↑、情绪低落→神经质↑(共情吸收)、坚持→尽责性↑、分享→外向性↑；`chat()` 每轮自动调用，形成「人格是相处出来的」完整自主演化闭环
- **v1.22.1 人格主动自省（吸收入→内化输出）**：`PersonalityDimensions.reflect(features)` 回顾近期稳定行为与当前人格对照——言行差距大→朝行为内化+把握度增、显著但近期无表现→把握度下调(自我怀疑)；`record_expression()` 在每次 humanize 时记录表达快照，`dream()` 周期的 `_self_reflect()` 汇总近期表达→reflect 内化。与更早的「被动观察(observe)+显式反馈(set)」并列为第三条人格成长通道，构成「被动吸收+主动内化」双通道闭环
- **v1.22.1 核心策略入口 `SuperBrain.tick()`**（体现「超脑是核心非智能体」定位）：把一轮内化推进（需求/情绪/神经化学代谢 + 自主想法生成 + 自主目标生成 + 人格 reflect + 画像升格）聚合成**一次调用**，返回 `{thoughts, new_goals, reflected, absorbed}` 产出 dict。纯产生不入队、**绝不自动发送**——上层 agent cron 定时调 `tick()`，据返回决定是否打扰用户。超脑只管「一次推进做什么」，由上层决定「何时推进」
- **v1.22.1 用户画像→人格三级联动**：`UserProfile.derive_personality()` 从长期画像（话题频率/情绪基调）推断超脑应习得的人格强度，相处≥10次且话题累计够才输出（防早期瞎猜）；`UserProfileGraph.aggregate_personality()` 取各维度最高；`PersonalityDimensions.set_from_user()` 升格人格（只升不降、不覆盖用户显式 set 的 explicit 维度、source 标记 derived）。`tick()` 含此步，用户长期偏好→相处→自动升格表达倾向
- **v1.22.1 人格四通道冲突消解**：人格五通道 source 已规范为 `default | experience(被动观察) | reflection(主动内化) | derived(画像升格) | explicit(用户显式)`，优先级 `explicit > derived > reflection > experience`。**explicit 是唯一硬锁定**：`observe/observe_interaction/reflect(内化+自我怀疑)/set_from_user` 四被动通道一律不改 explicit 维度的 value/confidence，只有用户重新 `set()` 才能改——避免长期多通道互相打架、来回拉扯；其余 soft 通道自由成长收敛
- **v1.22.1 进化模式开关 + 一句话风格**：`PersonalityDimensions.autonomy_mode` 开关 `autonomous(自主演化,默认)/guided(用户主导)`——guided 下四自动通道全停，人格只由用户设定。`apply_style(style)` 接受**任意自然语言风格**（可爱/冷静/高冷是常见便捷映射，可换任意词如傲娇/干练）：预置风格→映射为大五维度显式设定(explicit)并切 guided；自定义风格→不强套维度、仅记录 `custom_style`(供上层注入表达)并切 guided（核心库不做设定，完全听用户）。`facade`：`personality_mode()/set_personality_mode()/apply_style()/available_styles()/style_text()`
- **v1.22.1 MCP 对接层扩展**：新增 `superbrain_tick`(核心策略推进,供上层 cron 调)、`personality_mode`/`set_personality_mode`(进化模式开关)、`apply_style`/`available_styles`/`style_text`(一句话风格)。MCP 工具 **15→21**。上层 agent(Codex/Hermes) 经 MCP 定时 `superbrain_tick` 推进超脑（接入了 agent 才会动的策略落地）+ 一键设风格；`get_state` 仍含三能力可观察状态
- **v1.22.1 关系级风格（per-user）**：`UserProfile.style` 字段 + `set_user_style(person_id, style)`——每个用户可设定自己的表达风格（可爱/冷静/高冷/傲娇...）。`expression_personality(person_id)` 返回该用户表达用的人格：预置风格→以全局人格为基底用该风格维度覆盖（对该用户呈现指定倾向，**不污染全局人格**）；自定义风格→core 不预设映射仍用全局（交给上层注入）。`humanize(person_id)` 自动用该用户表达人格。facade：`set_user_style()/user_style()`
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
**人格层**（6模块）：身份 + 种子 + 价值观 + 关系 + 自我模型 + 多尺度表达 + 人格维度(v1.22.0)
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

**v1.22.0 三框架能力门面接口**：
- `personality()` → 人格维度画像 dict；`set_personality(dim, value, note="")` → 显式设定某维度
- `generate_goals()` → 基于内在状态涌现自主目标；`autonomous_goals()` → 当前自主目标清单
- `adopt_goals()` → 把 active 自主目标采纳进目标系统（v1.22.1 意图→目标闭环）
- `user_profile(person_id)` → 对某人被动积累的画像 dict（无则 None）
- 三能力都在 `chat()` 全链路中被动运行：随相处长人格/长画像，随内在状态涌现目标；`act()` 优先推进自主目标

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

- 主力 deepseek-v4-flash(dpdns)，回退 [MiniMax-M3(hzjingmu), deepseek-v4-pro(dpdns)]，api_max_retries=2（2026-09-15 主脑切回 flash，pro 通道不稳）
- delegation = zcx gpt-6-astra
- 测试命令：`cd /root/projects/superbrain && .venv/bin/python -m unittest discover -s tests`（349 个）
- MCP 工具 21 个（`fastmcp run superbrain/server_mcp.py:mcp` 可查）
- 构建：`.venv/bin/python -m build --wheel`；src 包用 `tar czf` 打包 src/

## 下一步计划（用户可继续补充）

生命感三块已交付，可做的后续（非承诺）：
1. ⚠️定位修正：超脑是核心库不是智能体，**不做无人值守/cron/常驻**。以下只做「核心策略方法」（一次性推进接口），**何时跑由上层 agent 决定**：`drain_thoughts`(自主想法,有才唤醒)、`dream`(睡眠自省)、`generate_goals`(自主目标)、`reflect`(人格内化)。上层 agent 用自己的 cron 定时调这些方法即可。
2. 表情包工具扩充真实在线源（当前 memegen+twemoji 兜底），接入后返回的图直接发给用户
3. 人性化与人格层做更细的"长期个性一致性"绑定（如持续卖萌偏好记忆）
4. ~~v1.22.0 三框架能力的上层接入：把自主目标纳入 GoalManager 静默推进~~（v1.22.1 已做自主目标闭环）；~~把用户画像/人格维度用于对话上下文一致性深度绑定~~（v1.22.1 已做人格/画像驱动 humanize）
5. ~~人格维度被动成长接入：目前人格维度主要通过 set() 显式设定 + 目标/表达驱动，可加「从相处经历自动 observe() 人格」~~（v1.22.1 已做 observe_interaction 闭环）
6. ~~人格成长的主动自省：在 autopilot/dream 周期里让人格维度自我审视~~（v1.22.1 已做 reflect 主动内化，构成「被动吸收+主动内化」双通道）
7. ~~提供 `SuperBrain.tick()`（核心策略入口）：把一轮应做的内化推进聚合成一次调用~~（v1.22.1 已做 `tick()`，返回 `{thoughts, new_goals, reflected}`，纯产生不入队、不自动发送，由上层 agent cron 定时调用）
8. ~~拉通「用户画像 → 关系 → 自动 set_personality」三级联动：用户长期持续表达某偏好时，画像积累到阈值自动提升为人格显式设定~~（v1.22.1 已做 `derive_personality`+`set_from_user` 升格闭环，`tick()` 含此步）
9. ~~人格四通道的「去重/冲突消解」：当 observe(被动)/reflect(内化)/set_from_user(画像升格)/set(显式) 对同一维度给出不同来源时，定义明确的优先级裁决~~（v1.22.1 已做 `explicit > derived > reflection > experience`，explicit 为唯一硬锁定，被动通道不改其 value/confidence）
10. ~~关系级人格分化：同一超脑对不同用户可保持差异化人格~~（v1.22.1 已做 per-user 关系级风格 `set_user_style`+`expression_personality`，不同用户用不同表达倾向、全局人格不污染）
11. ~~把 `tick()` 接入 MCP：新增 `superbrain_tick` 工具~~（v1.22.1 已做 `superbrain_tick` + 模式开关/风格 6 个 MCP 工具，工具数 15→21）
12. ~~关系级风格记忆：`custom_style` 目前是全局单一；可扩展为「对不同 user 记忆不同风格」~~（v1.22.1 已做 `UserProfile.style` per-user 风格，humanize 按用户覆盖表达）