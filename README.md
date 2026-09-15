[简体中文](README.md) | [English](README_EN.md)`n`n# 超脑 SuperBrain`n`n**情感认知内核 + 可靠记忆层的自主 Agent 框架。**`n`nSuperBrain v2.0.0 是纯 Python 阶段的完整基线，也是项目对外发布的第一个正式版本（Release 1.0.0）。它将需求驱动、情绪动力学、神经化学动量、人格、自我模型、关系演化、主动目标、主动思考和多层记忆组合成一个可嵌入的 Agent 内核。`n`n![SuperBrain 架构图](docs/images/architecture.svg)`n`n> 这里的“仿人类”是可检查、可调整的计算模型，不代表真实意识、生物大脑仿真或已证明的共情能力。`n`n## 核心能力

```
身份层      Identity（锚点 + 时间身份：过去/现在/将来）
情绪层      EmotionGradient（内部≠对外）+ 神经化学动量（多巴胺/血清素/皮质醇）
认知层      PSI 需求驱动 + 元认知反思 + EG-MRSI 完整版（元认知向量自改进）
种子层      SeedBank（去重强化 + 置信度门槛 + 衰减）
安全层      ValueSystem（核心不可变原则）
记忆层      四类记忆（工作/情景/语义/程序）+ 事件日志 + 概念图
          + 四路检索（向量/关键词/图谱/概念）+ 遗忘曲线 + 时间体感
          + PISA schema 演化（同化/顺应/创造）
自我层      SelfModel（过去/现在/将来自我叙事）
行动层      Function-calling + 权限门禁 + LLM 规划
进化层      自动学习（LLM 抽取）+ 经验/技能蒸馏 + 睡眠计算（dream）
注意层      GWT 全局工作空间（多模块竞争广播）
生命感层    AutonomousThought（自主思考/想念/关心/好奇/分享）
          + HumanizeEngine（卖萌/亲昵/情绪化表达）+ 表情包搜索工具
运行层      Scheduler（主动运行）+ 滚动摘要压缩 + 自动保存 + 统一持久化
```

## 安装

```bash
pip install superbrain
# 或从源码
pip install -e .
```

## 快速上手

```python
from superbrain import SuperBrainAgent, from_env

agent = SuperBrainAgent(from_env())
agent.identity.name = "小凌"
agent.chat("你好，我特别喜欢用 deepseek")

# 内在状态
print(agent.state_snapshot())

# 持久化（一个 .db 文件 = 整个大脑）
agent.save()

# 恢复
agent.load()
```

## 设计理念

- **内容冻结**：记忆永不改写，只建立语义关联，杜绝 AI 幻觉污染
- **情绪-记忆耦合**：记忆带情绪标签，情绪影响检索偏好
- **全局工作空间**：多模块竞争注意力，最强广播驱动统一行动
- **自我连续**：重启后身份、人格、记忆、情绪、种子、关系全部恢复
- **零依赖**：纯 Python 标准库，一个 SQLite 文件即可带走

## 测试

```bash
python -m unittest discover -s tests
```

## License

MIT

