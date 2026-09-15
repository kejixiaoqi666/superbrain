# 超脑 SuperBrain

**情感认知内核 + 可靠记忆层的自主 Agent 框架。** 纯 Python 标准库，零依赖。

一个拥有内在需求、情绪、记忆、人格、自主目标和主动行动能力的智能体核心库。设计哲学：**内核只做框架，不做设定**——人格、关系、记忆都是相处出来的，而非预设。

## 核心能力

```
认知层      需求驱动(PSI) + 情绪梯度(内部≠对外) + 神经化学 + 元认知 + 注意力(GWT)
记忆层      SQLite单文件 + FTS5全文 + 哈希向量 + 概念图 + 四路检索(RRF)
          + 遗忘曲线 + 分层tier(core/recall/archival) + 30天对话浓缩 + 1GB物理护栏
人格层      大五维度(被动观察/主动内化/画像升格/显式设定 四通道)
          + 进化模式开关(自主演化/用户主导) + 一句话风格(可爱/冷静/高冷/傲娇...)
          + 关系级 per-user 风格
关系层      自主关系定位(依恋/信任/熟悉, 无绑定标签) + 被动用户画像
自主性      自主思考(想念/关心/好奇/分享/修复冲动) + 自主目标生成→采纳→推进
          + 情绪动力学(心境/时间衰减/情绪感染/自豪/愧疚/低落保守)
          + `tick()` 核心策略入口(供上层定时调)
表达层      HumanizeEngine(人格/画像驱动) + 底层表达元素库 + 表情包工具
对接层      Python 门面 / HTTP 服务 / MCP server(21 工具) 三入口
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

## 记忆生命周期（v2.0.0）

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
- **情绪-记忆耦合**：记忆带情绪标签，心境偏置检索
- **自我连续**：重启后身份、人格、记忆、情绪、种子、关系、会话全部恢复
- **零依赖**：纯 Python 标准库，一个 SQLite 文件即可带走

## 测试

```bash
python -m unittest discover -s tests   # 349 个测试
```

## License

MIT