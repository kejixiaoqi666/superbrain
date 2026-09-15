"""超脑 SuperBrain —— 集成门面（facade）。

其他 agent 接入超脑的唯一入口：一行代码装配全部 30+ 模块，
暴露统一接口，隐藏内部复杂性。

用法：
    from superbrain import SuperBrain
    brain = SuperBrain.from_env()   # 一行装配（自动读环境变量配 LLM）
    brain.chat("你好")              # 对话（含认知+记忆+人格全链路）
    brain.remember("用户喜欢茶")     # 记一条
    brain.recall("用户喜欢什么")     # 查记忆
    brain.state()                   # 看内在状态
    brain.save() / brain.load()     # 持久化 / 恢复
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .core.agent import SuperBrainAgent, AgentConfig
from .core.llm import LLMProvider, from_env as _llm_from_env
from .core.memory.store import MemoryStore
from .core.meme_tool import search_meme


class SuperBrain:
    """超脑集成板块：门面类，封装认知+记忆+人格+行动+进化全链路。

    其他 agent 只需 `SuperBrain.from_env()` 即可使用全部能力，
    不必关心内部 30+ 模块如何装配。
    """

    def __init__(self, llm: Optional[LLMProvider] = None,
                 store: Optional[MemoryStore] = None,
                 config: Optional[AgentConfig] = None) -> None:
        llm = llm or _llm_from_env()
        self._agent = SuperBrainAgent(llm, store=store, config=config)

    # ---------- 工厂 ----------

    @classmethod
    def from_env(cls, **kwargs) -> "SuperBrain":
        """从环境变量一键装配（自动配 LLM、记忆库）。

        环境变量：
        - SUPERBRAIN_LLM_BASE / SUPERBRAIN_LLM_KEY / SUPERBRAIN_LLM_MODEL
        - SUPERBRAIN_DB（记忆库路径，默认 ~/.superbrain/brain.db）
        """
        return cls(**kwargs)

    @classmethod
    def from_llm(cls, llm: LLMProvider, store: Optional[MemoryStore] = None,
                 **kwargs) -> "SuperBrain":
        """用指定 LLM 装配（供其它 agent 传入自己的模型）。"""
        return cls(llm=llm, store=store, **kwargs)

    # ---------- 统一接口（隐藏内部复杂性） ----------

    def chat(self, message: str, person_id: str = None) -> str:
        """对话：认知（需求/情绪/神经化学/元认知/注意力）→ 记忆检索 → 行动。

        person_id 传入时，超脑随相处自主演化对该人的关系（信任/熟悉/依恋增长 + 自主重新定性）。
        """
        return self._agent.chat(message, person_id=person_id)

    def orientations(self) -> dict:
        """超脑对每个人的自主关系定位（相处中自主形成，非绑定标签）。"""
        return self._agent.relationships.orientations()

    def expression_elements(self, orientation: str = None) -> dict:
        """底层表达元素库：某关系定位下超脑可选用的言语元素（框架范围，非锁定）。

        orientation=None 返回全部分类元素清单；传入 lover/friend/close 等返回该定位可选范围。
        """
        from .core import expression_library as el
        if orientation is None:
            return el.all_elements()
        return el.elements_for(orientation)

    def remember(self, content: str, scope: str = "user",
                 tier: str = "recall", **kwargs) -> str:
        """写入一条记忆。返回节点 id。"""
        node = self._agent.remember(content, scope=scope, tier=tier, **kwargs)
        return node.node_id

    def recall(self, query: str, k: int = 5) -> List[Dict]:
        """检索记忆。返回 [{content, score, why}] 列表。"""
        hits = self._agent.recall(query, k=k)
        return [{"content": n.content, "score": round(s, 4), "why": w}
                for n, s, w in hits]

    def state(self) -> dict:
        """内在状态快照（需求/情绪/神经化学/元认知/注意力）。"""
        snap = self._agent.state_snapshot()
        snap["attention"] = self._agent.attention.history[-1].to_dict() \
            if self._agent.attention.history else None
        return snap

    def save(self, path: Optional[str] = None) -> str:
        """持久化整个大脑（一个 db = 全部状态）。"""
        return self._agent.save(path)

    def load(self, path: Optional[str] = None) -> bool:
        """从持久化恢复。"""
        return self._agent.load(path)

    def dream(self, window_hours: float = 24.0) -> List[str]:
        """睡眠计算：回顾记忆提炼经验。"""
        return self._agent.dream(window_hours)

    def act(self, goal=None):
        """主动行动：需求派生目标→规划→执行。"""
        return self._agent.act(goal)

    def generate_thoughts(self):
        """自主思考：基于内在状态产生主动想法（纯产生，不入队）。返回本次新产生的想法列表，
        直接使用返回值发送；如需队列消费，先 enqueue 再 drain_thoughts()。"""
        return self._agent.autonomous.generate(
            self._agent.needs, self._agent.emotion, self._agent.relationships)

    def drain_thoughts(self):
        """取出待发的自主消息队列（供上层灌进对话）。"""
        return self._agent.autonomous.drain()

    def humanize(self, text: str, person_id: str = None) -> str:
        """人性化表达包装：按情绪 + 与该人亲密度/昵称生成口语化文本。"""
        emotion = self._agent.emotion.state
        familiarity, nickname = 0.5, ""
        if person_id:
            rel = self._agent.relationships.get(person_id)
            if rel:
                familiarity, nickname = rel.familiarity, rel.nickname
        return self._agent.humanize.humanize(
            text, emotion, familiarity=familiarity, nickname=nickname)

    def search_meme(self, query: str, limit: int = 5):
        """搜索表情包，返回 [{url, title, source}]。"""
        return search_meme(query, limit)

    def index_concepts(self, limit: int = 20) -> int:
        """抽取概念建图（GraphRAG）。"""
        return self._agent.index_concepts(limit)

    def deduplicate(self, threshold: float = 0.85) -> int:
        """合并近似记忆。"""
        return self._agent.deduplicate(threshold)

    def close(self) -> None:
        self._agent.close()

    # ---------- 内部透传（高级用法） ----------

    @property
    def agent(self) -> SuperBrainAgent:
        """底层 agent（高级用户直接访问全部模块）。"""
        return self._agent

    def __repr__(self) -> str:
        return (f"<SuperBrain v{self._agent.__class__.__module__.split('.')[0]} "
                f"mem={self._agent.store.count_nodes()} "
                f"need={self._agent.needs.get_dominant_need()[0].value if self._agent.needs.get_dominant_need()[0] else '无'}>")
