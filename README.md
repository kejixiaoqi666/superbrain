[简体中文](README.md) · [English](README_EN.md)

# 🧠 SuperBrain 超脑

> **情感认知内核 + 可靠记忆层的自主 Agent 框架** · v1.0.0 · 纯 Python 标准库 · 零第三方依赖

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-349%20passed-brightgreen)
![Deps](https://img.shields.io/badge/Dependencies-0-important)

一个拥有**内在需求、情绪、记忆、人格、关系、自主目标**的智能体核心库。设计哲学：**内核只做框架，不做设定**——人格、关系、记忆都是相处出来的，而非预设。LLM 负责语言，超脑负责状态、偏置、记忆与行动接口。

![SuperBrain 架构图](docs/images/architecture.svg)

> "情绪""关心""想念"在这里是明确的数据结构、阈值、更新函数与状态转移——**可检查、可调整、可持久化的计算模型**，不代表真实意识或对生命/共情的宣称。

---

## ✨ 亮点速览

| 维度 | 一句话 |
|---|---|
| 🧭 **认知** | 五大需求驱动 + 元认知反思 + 神经化学模拟 |
| ❤️ **情绪** | 八维状态 + 心境慢变量 + 时间衰减 + 情绪感染 + 自豪愧疚 |
| 🧠 **记忆** | 四路检索（向量/FTS5/图谱/概念图）+ RRF 融合 + 遗忘曲线 + 浓缩 |
| 🪪 **人格** | 大五维度四通道成长 + 进化开关 + 一句话风格 + per-user 风格 |
| 🤝 **关系** | stranger→acquaintance→friend→close→lover 自主演化 |
| 🚀 **自主** | 主动思考（想念/关心/好奇/分享/修复）+ 自主目标 + tick() |
| 🔌 **对接** | Python 门面 / HTTP REST / MCP（21 工具）三入口 |

---

## 🧭 核心能力

```
认知层     PSI 需求驱动（重要性习得）+ 情绪梯度（内部≠对外）+ 神经化学（多巴胺/血清素/皮质醇）
          + 元认知反思（谨慎度/策略偏好/自调参）+ GWT 全局工作空间竞争广播
记忆层     SQLite 单文件 + FTS5 全文 + 哈希向量 + 概念图 + 四路检索(RRF)
          + 艾宾浩斯遗忘曲线 + 复习强化 + tier(core/recall/archival)
          + 遗忘-重激活 + 30 天对话浓缩 + 容量护栏 + Dream/PISA/Distill
人格层     大五中性骨架（被动观察/主动内化/画像升格/显式设定 四通道）
          + 冲突消解 + 进化模式开关 + 一句话风格 + 关系级 per-user 风格
关系层     自主关系定位（熟悉/信任/依恋/昵称/边界/期待）+ 被动用户画像
自主层     AutonomousThought（想念/关心/好奇/分享/修复）+ 自主目标生成→采纳→推进
          + 情绪动力学（心境/衰减/感染/自豪愧疚/低落保守）+ tick() 核心策略
表达层     HumanizeEngine（人格/画像驱动）+ 表达元素库 + 表情包工具
对接层     Python 门面 / HTTP 服务 / MCP server（21 工具）
```

---

## ❤️ 情绪与情感机制（重点）

### 1. 连续状态，而非情绪标签
`EmotionalState` 带八维：`valence`(愉悦)、`arousal`(唤醒)、`dominance`(掌控)、`confidence`(自信)、`certainty`、`safety`、`fatigue`、`attachment`，加慢变量 `mood` 与社会情绪 `pride/guilt`。内部状态与对外表达分离（`Expression`）——能表达"内部低落但为了不让人担心而积极"。

### 2. 需求如何产生情绪
`NeedDriveSystem` 维护五项需求（当前值/目标/衰减率/波动/重要性），驱动力 = `max(0, target-current)×importance`，缺口最大的成主导需求。`EmotionGradient.update()`：`v_target = clamp(2×均满足−1, −1, 1)`，指数平滑更新 valence；需求变化幅度驱动 arousal。可读可改参数的需求→情绪映射。

### 3. 心境慢变量
`mood`（-1..1）是长期基线：每次 update 以极小速率 `0.02` 向 `v_target×0.6` 靠近。连续积极/消极经历慢慢改变底色，单次事件不立即改写心境；它还偏置记忆检索。

### 4. 情绪时间衰减
`elapse(dt, tau=6h)` 用 `rate=1−exp(−dt/tau)` 让瞬时 valence 向 mood 回归——"事件会过去，心境底色还在"。

### 5. 情绪感染
`update(..., contagion)` 把他人情绪作为 −1..1 外部信号，`contagion×0.4` 加到 valence 目标——与他人低落相处时被牵引（共情）。

### 6. 自豪与愧疚
`social_update(pride, guilt)`：做成/帮到人 → valence+dominance 上行、累积 pride；失责/伤害关系 → 下行、累积 guilt。数值 clamp、增量受参数约束，防止一次锁死。

### 7. 愧疚→修复冲动
`generate()` 检查 `guilt≥0.4`，对最熟悉的关系生成 `REPAIR` 想法（"想道歉/补偿，别让关系疏远"）——愧疚驱动行为回路。

### 8. 低落保守与倾诉
valence<−0.3 抑制好奇探索（不想冒险）、倾向"先稳住眼前"；val<−0.4 倾向寻求陪伴。

### 9. 情绪一致性记忆
`recall()` 以 `sim=mood×node.valence` 为偏置：低落时偏向想起负面、高涨偏向正面，不一致轻微抑制——情绪影响"记住/想起什么"，但不伪造检索结果。

### 10. 人格维度塑造情感表达
大五维度从中性(0.5)开始，四通道成长（互动关键词 `observe`、近期表达 `reflect`、画像 `set_from_user`、显式 `set`），explicit 最高优先，guided 关闭自动通道。

### 11. humanize 表达层
接收内部情绪 + 人格显著维度 + 关系亲密度 + 用户画像，把生成内容包装为口语化表达；可选开关，不修改内在状态。

---

## 🧠 记忆生命周期

```
记录   寒暄过滤 + 内容指纹去重（不"一句话记一句"）
遗忘   长期不用的降级 archival（≠删除，强相关提起自动重激活）
浓缩   超 30 天窗口后 LLM/启发式提炼为要点常青记忆，细节降级
加固   Dream 睡眠整理 / 蒸馏成 Experience·Skill / PISA 图式演化 / 概念图 GraphRAG
护栏   记忆库物理上限默认 1GB（可配）+ 长会话内存有界
```

## 🪪 人格与进化

- 大五中性骨架 × 四通道（被动观察 / 主动内化 / 画像升格 / 显式设定）
- 进化模式开关：`autonomous`（自主演化）/ `guided`（用户主导，自动通道全停）
- 一句话风格：`apply_style("可爱"/"冷静"/"高冷"/"傲娇"...)`，任意自然语言，不锁定清单
- 关系级 per-user 风格：不同用户不同表达倾向

## 🔌 三种接入

```
Python   SuperBrain.from_env()  一行装配，能力最全，嵌入现有 Agent
HTTP     python -m superbrain.server  零依赖 REST API（/chat /remember /recall /state ...）
MCP      python -m superbrain.server_mcp  21 工具，对接 Codex / Hermes
```

## 🚀 快速上手

```python
from superbrain import SuperBrain

brain = SuperBrain.from_env()              # 一行装配（需设 SUPERBRAIN_LLM_KEY）
reply = brain.chat("你好，我特别…")          # 需求→情绪→记忆→人格→表达 全链路
brain.remember("用户喜欢乌龙茶")             # 写记忆（一个 .db = 整个大脑）
hits = brain.recall("饮品偏好")              # 检索
brain.apply_style("可爱")                    # 一句话人格设定
out = brain.tick()                          # 核心推进（供上层定时调）
brain.save(); brain.load()                  # 持久化/恢复，重启不失忆
```

## 📊 性能

| 项 | 数据 |
|---|---|
| 检索 | 5000 条记忆 FTS5 候选路径 ~5ms（top-k）|
| 内存 | 200 轮对话峰值 0.34MB，长会话有界 |
| 建库 | 2000 条 ~1.5s |
| 测试 | 349 全过，pyflakes 0 |

## 🎯 设计理念

- **可解释优先**：状态、阈值、公式、来源均可追踪
- **内容冻结**：记忆永不改写，只建语义关联，杜绝幻觉污染
- **人格长出来**：相处塑造 + 主动内化 + 用户设定，非预设
- **遗忘≠删除**：降级不丢，被提及即重激活
- **核心与模型解耦**：可接任意 LLM
- **默认克制**：自主产出只返回上层不自动发送

## ✅ 测试

```bash
python -m unittest discover -s tests   # 349 个测试
```

## 📁 目录

```
src/superbrain/
├── facade.py          SuperBrain 门面（推荐入口）
├── server.py          HTTP 服务        server_mcp.py  MCP server
├── __main__.py        CLI
└── core/              agent / llm / autonomous / autonomous_goals / user_profile
                       / humanize / cognition(需求·情绪·神经化学·元认知·自调)
                       / personality(身份·种子·价值观·关系·自我·大五维度)
                       / memory(存储·检索·嵌入·概念图·蒸馏·遗忘·Dream·PISA)
```

## 📄 License

MIT