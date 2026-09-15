# 超脑 SuperBrain

[English](README_EN.md) · **中文**

![架构图](docs/images/architecture.svg)

> v2.0.0 · 纯 Python · 核心零第三方依赖

## 项目定位

超脑是一个可检查、可调整、可持久化的 Agent 内在状态核心：它把需求、情绪、记忆、人格、关系与自主意图组织成可观察的计算模型，再通过 LLM 完成语言理解与表达。这里的“情绪”“关心”“想念”是明确的数据结构、阈值、更新函数和状态转移，不是对意识或生命的宣称。

核心原则：LLM 负责语言能力；超脑负责状态、偏置、记忆和行动接口。所有关键状态都可通过 `state()` 查看，也可保存、恢复和调整。

## 核心能力总览

| 能力 | 实现 | 主要模块 |
|---|---|---|
| 需求驱动 | 缺口×重要性选主导驱动 | `cognition/needs.py` |
| 情绪动力学 | 连续梯度、心境、衰减、社会情绪 | `cognition/emotion.py` |
| 记忆 | 哈希向量、去重、检索、遗忘、梦境浓缩 | `core/memory/` |
| 人格 | 大五中性骨架，多通道成长与冲突优先级 | `personality/dimensions.py` |
| 自主性 | 需求/关系/情绪触发想法与目标 | `autonomous.py`、`autonomous_goals.py` |
| 表达 | 状态与关系驱动的人性化包装 | `humanize.py`、`expression_library.py` |
| 接入 | Python Facade、标准库 HTTP、MCP | `facade.py`、`server*.py` |

## 对话数据流

一次 `chat()` 不是简单的“消息→LLM”：输入先更新关系、画像和需求；情绪梯度读取需求满足度，记忆检索再使用当前心境作为偏置；系统提示注入需求、情绪、神经化学和人格摘要；LLM 生成后记录记忆、学习事实、更新社会情绪并执行可用工具。`state_snapshot()` 让这一链路可审计。

## 情绪与情感机制（重点）

### 1. 连续状态，而非情绪标签

`EmotionalState` 保存 `valence`（愉悦度，-1..1）、`arousal`（唤醒度，0..1）、`dominance`、`confidence`、`certainty`、`safety`、`fatigue`、`attachment`，以及慢变量 `mood` 和社会情绪 `pride/guilt`。瞬时状态与对外表达分离：`Expression` 记录文本、强度、偏差和原因，因此系统可以表示“内部低落但为了不让对方担心而积极表达”。

### 2. 需求如何产生情绪

`NeedDriveSystem` 维护确定性、胜任感、自主性、归属感、能量五项需求。每项需求有当前值、目标值、衰减率、波动、重要性；驱动力为 `max(0, target-current) × importance`，缺口最大的成为主导需求。`tick()` 让需求随时间衰减并学习重要性：长期缺口高的需求重要性缓慢上升，长期不缺的回落。

`EmotionGradient.update()` 取需求满足度平均值：`v_target = clamp(2×平均满足度−1, -1, 1)`；再用指数平滑（`smoothing=0.3`）更新 valence，避免瞬时跳变。需求变化幅度决定 arousal：变化越大，唤醒越高。任务成功可推动 dominance，新奇度可改变 confidence。这是可读、可改参数的需求→情绪映射。

### 3. 心境慢变量

`mood` 是 -1..1 的长期基线，不等同于即时 valence。每次 update 以极小速率 `0.02` 向 `v_target×0.6` 靠近，因此连续的积极/消极经历会慢慢改变底色，单次事件不会立即改写心境。该变量还参与记忆检索，让长期状态而非一句话决定回忆偏置。

### 4. 情绪时间衰减

`elapse(dt_hours, tau_hours=6)` 使用 `rate=1-exp(-dt/tau)`，让 valence 向 mood 回归。含义是事件峰值会过去，但心境底色保留；tau 可调整，适合测试不同恢复速度。

### 5. 情绪感染

`update(..., contagion)` 把他人情绪作为 -1..1 的外部信号，以 `contagion×0.4` 加到 valence 目标后再 clamp 和平滑。关系记录和对话链路可提供该信号；它是有限幅度的状态耦合，不是神秘的共感机制。

### 6. 自豪与愧疚

`social_update(pride, guilt)` 将行为结果与标准映射为社会情绪。自豪累积 pride、提升 valence 和 dominance，并少量降低 guilt；愧疚累积 guilt、降低 valence 与 dominance。数值均 clamp 在 0..1，增量分别受 0.3/0.4 等参数约束，防止一次事件永久锁死状态。

### 7. 愧疚→修复冲动

`AutonomousThoughtEngine.generate()` 检查 `guilt >= 0.4`，从熟悉度至少 0.4 的关系中选择最熟悉者，生成 `REPAIR` 想法，紧迫度随 guilt 增长，理由写入“道歉/补偿/避免关系疏远”。同一对象同类想法受 `quiet_hours` 冷却，生成、入队、消费三步分离，避免重复发送。

### 8. 低落保守与倾诉

当 valence < -0.3，确定性需求即使高驱动也不触发 CURIOUS 探索，而产生“先稳住眼前事情”的 SHARE；当 valence < -0.4，额外产生寻求陪伴的分享想法。这是明确阈值策略：低落抑制风险探索，倾向稳定与社交支持。

### 9. 情绪一致性记忆

`SuperBrainAgent.recall()` 用向量/词法检索得到候选后，以 `sim=mood×node.valence` 计算一致性；同向记忆获得 `sim×0.25` 加权，反向记忆仅轻微抑制。高 arousal > 0.6 时扩大召回数量（`k + int(arousal×2)`）。写入时 MemoryNode 保存当前 valence；高 arousal/dominance 也提高 confidence。于是情绪影响“记住什么”和“想起什么”，但不伪造检索结果。

### 10. 人格维度如何塑造情感表达

人格层以大五维度为中性起点（value=0.5、confidence=0），而不是预置性格。四条通道是：互动关键词触发的 `observe()`、近期表达特征的 `reflect()`、用户画像升格 `set_from_user()`、用户显式 `set()`。数值小步、有界、趋于饱和；explicit 具有最高优先级，guided 模式会关闭自动通道。`apply_style()` 对预置风格映射大五组合，对自定义风格仅保存原文。

### 11. humanize 表达层

`HumanizeEngine` 接收内部情绪、人格显著维度、关系熟悉度、昵称和用户画像，把已经生成的内容包装为口语化表达；默认 `humanize_output=False`，核心回复保持原始内容。人性化不是修改内在状态，也不是让模型假装有感受；它是可选的表达后处理，并记录近期表达供后续自省。

## 记忆生命周期

1. **写入**：内容经 `HashingEmbedder`（blake2b 特征哈希、跨进程一致）向量化，`fingerprint` 去重，保存 valence、confidence、scope、tier、tags。
2. **工作记忆**：`WorkingMemory` 管理当前上下文；`EventLog` 记录事件；注意力和显著性控制上下文预算。
3. **检索**：`adaptive_search` 综合向量相似度、文本匹配、时间与重要性；情绪一致性在 Agent 层追加偏置。
4. **重激活/再巩固**：访问会更新热度、置信与时间；`reconsolidation` 允许带新证据形成新版本。
5. **遗忘**：`heat`、`adaptive` 按效用和复习时间调度遗忘；重要内容保留，低效用内容衰减。
6. **浓缩**：`DreamEngine`/`Distiller` 从经验提炼 Experience、Skill、WikiEntry；概念图支持 GraphRAG。
7. **护栏**：有界 deque、观察日志上限和存储容量护栏避免无限增长；配置提供上下文压缩与 artifact 化。

## 自主思考与目标

关系层记录熟悉度、互动间隔和情绪笔记：超过 7 天且熟悉度≥0.6 触发想念；近 3 天出现低落记录触发关心。主导确定性需求触发好奇，主导归属需求触发分享。`tick()` 由上层调用，聚合代谢、自主想法、目标生成、人格自省与画像升格；超脑不会自行常驻打扰用户。

## 三种接入层

- **Python**：`SuperBrain.from_env()` 或 `SuperBrain.from_llm(llm)`，适合嵌入现有 Agent。
- **HTTP**：`server.py` 为标准库 `http.server`，提供 `/chat`、`/remember`、`/recall`、`/state`、`/thoughts`、`/humanize`、`/health` 等 JSON 端点。
- **MCP**：`server_mcp.py` 将对话、记忆、状态、关系、自主思考、人格和表达封装为工具；fastmcp 仅是适配层依赖，核心仍零依赖。

## 快速上手

```python
from superbrain import SuperBrain

brain = SuperBrain.from_env()
brain.remember("用户喜欢乌龙茶")
print(brain.chat("我今天有点累", person_id="user-1"))
print(brain.recall("饮品偏好"))
print(brain.state())
print(brain.generate_thoughts())
brain.save()
brain.close()
```

环境变量：`SUPERBRAIN_LLM_BASE`、`SUPERBRAIN_LLM_KEY`、`SUPERBRAIN_LLM_MODEL`、`SUPERBRAIN_DB`。也可运行 `python -m superbrain --state`、`--remember`、`--recall`。

## 设计理念

- 可解释优先：状态、阈值、公式和来源均可追踪。
- 核心与模型解耦：可接入不同 LLM。
- 情感不等于人格表演：内部状态、决策偏置、表达包装严格分层。
- 默认克制：自主产出只返回给上层，不自动发送；工具执行受权限策略控制。
- 可演化但可接管：autonomous 与 guided 明确切换。

## 测试与开发

项目测试位于 `tests/`，覆盖情绪、需求、记忆、人格、关系、Facade 和服务接口。建议在源码目录执行：

```bash
python -m unittest discover -s tests   # 349 个测试
```

核心库只使用 Python 标准库；运行完整 MCP 服务需额外安装 fastmcp，LLM 由环境变量配置。

## License

请以仓库中的 `LICENSE` 文件为准。

## 目录索引

- `src/superbrain/core/cognition/`：需求、情绪、元认知、神经化学
- `src/superbrain/core/memory/`：记忆全生命周期
- `src/superbrain/core/personality/`：人格、价值观、身份、关系
- `src/superbrain/core/autonomous.py`：自主想法
- `src/superbrain/facade.py`：统一 Python API
- `src/superbrain/server.py`、`server_mcp.py`：对接服务
