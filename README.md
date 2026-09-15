[简体中文](README.md) | [English](README_EN.md)

# 超脑 SuperBrain

**情感认知内核 + 可靠记忆层的自主 Agent 框架。**

SuperBrain v2.0.0 是纯 Python 阶段的完整基线，也是项目对外发布的第一个正式版本（Release 1.0.0）。它将需求驱动、情绪动力学、神经化学动量、人格、自我模型、关系演化、主动目标、主动思考和多层记忆组合成一个可嵌入的 Agent 内核。零依赖，纯 Python 标准库。

![SuperBrain 架构图](docs/images/architecture.svg)

> 这里的"仿人类"是可检查、可调整的计算模型，不代表真实意识、生物大脑仿真或已证明的共情能力。

## 核心能力

```
身份层      Identity（锚点 + 时间身份：过去/现在/将来）
情绪层      EmotionGradient（内部≠对外）+ 神经化学动量（多巴胺/血清素/皮质醇）
          + 情绪动力学（心境慢变量 / 时间衰减 / 情绪感染 / 自豪愧疚 / 低落保守）
认知层      PSI 需求驱动（需求重要性习得）+ 元认知反思 + 情绪-记忆一致性回路
种子层      SeedBank（去重强化 + 置信度门槛 + 衰减）
安全层      ValueSystem（核心不可变原则）
记忆层      四类记忆（工作/情景/语义/程序）+ 事件日志 + 概念图
          + 四路检索（向量/关键词/图谱/概念）+ 遗忘曲线 + 时间体感
          + PISA schema 演化（同化/顺应/创造）
          + 记忆生命周期（遗忘-重激活 / 30天浓缩 / 1GB 护栏）
自我层      SelfModel（过去/现在/将来自我叙事）
人格层      大五维度（被动观察/主动内化/画像升格/显式设定 四通道）
          + 进化模式开关 + 一句话风格 + 关系级 per-user 风格
行动层      Function-calling + 权限门禁 + LLM 规划
进化层      自动学习（LLM 抽取）+ 经验/技能蒸馏 + 睡眠计算（dream）
注意层      GWT 全局工作空间（多模块竞争广播）
生命感层    AutonomousThought（自主思考/想念/关心/好奇/分享/修复冲动）
          + HumanizeEngine（卖萌/亲昵/情绪化表达）+ 表情包搜索工具
自主性      AutonomousGoal（自主目标生成→采纳→推进）+ tick() 核心策略入口
运行层      Scheduler（主动运行）+ 滚动摘要压缩 + 自动保存 + 统一持久化
对接层      Python 门面 / HTTP 服务 / MCP server（21 工具）
```

## 安装

```bash
pip install superbrain
# 或从源码
pip install -e .
# 安装 MCP 对接层（对接 Codex/Hermes 时）
pip install superbrain[mcp]
```

## 快速上手

```python
from superbrain import SuperBrain

# 一行装配（自动读环境变量配 LLM + 默认记忆库；需设 SUPERBRAIN_LLM_KEY）
brain = SuperBrain.from_env()

# 对话（需求→情绪→记忆→人格→表达 全链路）
reply = brain.chat("你好，我特别喜欢用 deepseek")

# 写入 / 检索记忆（一个 .db 文件 = 整个大脑）
brain.remember("用户喜欢蓝色汽车")
hits = brain.recall("用户喜欢什么")

# 内在状态
print(brain.state())

# 人格：一句话设定（任意自然语言，不锁定清单）
brain.apply_style("可爱")        # 或 冷静/高冷/傲娇/干练...

# 睡眠：记忆浓缩 + 遗忘降级 + 人格自省
brain.dream()

# 核心策略推进（供上层 agent 定时调用/tick，不自动发送）
out = brain.tick()               # {"thoughts":.., "new_goals":.., ...}

# 持久化 / 恢复
brain.save()
brain.load()
```

## 三种接入方式

| 方式 | 适用 | 说明 |
|---|---|---|
| **Python 门面** | 同机 Python agent | `SuperBrain` 一行装配，能力最全 |
| **HTTP 服务** | 跨语言 / 远程 / 独立服务 | `python -m superbrain.server`，零依赖 REST API |
| **MCP server** | 对接 Codex / Hermes | `python -m superbrain.server_mcp`，21 个工具暴露大脑能力 |

详见 [`INTEGRATION.md`](INTEGRATION.md)。

## 记忆生命周期

```
记录   寒暄过滤 + 内容指纹去重（不"一句话记一句"）
遗忘   长期不用的降级 archival（≠删除，提起来自动重激活）
浓缩   超 30 天窗口后用 LLM(或启发式)提炼为要点常青记忆，细节降级
护栏   记忆库物理上限默认 1GB（可配）
```

## 设计理念

- **内容冻结**：记忆永不改写，只建立语义关联，杜绝 AI 幻觉污染
- **人格长出来**：相处经历被动塑造 + 主动内化 + 用户显式设定，非预设
- **遗忘≠删除**：记忆降级不丢失，被重新提及即重激活
- **情绪-记忆耦合**：记忆带情绪标签，心境偏置检索（情绪一致性记忆提取）
- **全局工作空间**：多模块竞争注意力，最强广播驱动统一行动
- **自我连续**：重启后身份、人格、记忆、情绪、种子、关系、会话全部恢复
- **零依赖**：纯 Python 标准库，一个 SQLite 文件即可带走

## 测试

```bash
python -m unittest discover -s tests   # 349 个测试
```

## License

MIT