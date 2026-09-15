"""核心 Agent：记忆层 + 认知层协同的主循环。

感知 → 需求评估 → 情绪更新 → 记忆检索（受情绪/需求影响）→ 行动 → 学习。

协同点：
- 情绪影响记忆写入权重（高唤醒/高支配时记忆更重要，更值得记）
- 主导需求决定行动倾向（如确定性需求高 → 主动检索/探索）
- 情绪/需求状态注入 system prompt，让 LLM 感知"内在状态"
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .cognition.needs import NeedDriveSystem, NeedType
from .cognition.emotion import EmotionGradient
from .cognition.self_tune import SelfTuner
from .cognition.neurochem import NeuroChemistry
from .cognition.metacognition import Metacognition
from .memory.store import MemoryStore
from .memory.node import MemoryNode, fingerprint
from .memory.embeddings import HashingEmbedder
from .memory import retrieval

from .memory.working import WorkingMemory
from .memory.eventlog import EventLog
from .memory.time_sense import fuzzy_time
from .memory.pisa import SchemaEngine
from .memory.expression_guide import analyze_memory_scale, expression_guide
from .attention import AttentionEngine, attention_block
from .context_cleaner import clean_tool_output, clean_history_message, is_noise
from .gwt import GlobalWorkspace
from .memory.distill import Distiller
from .memory.dream import DreamEngine
from .memory.concept import ConceptExtractor, ConceptGraph
from .memory import dedupe
from .llm import LLMProvider, estimate_tokens
from .tools import ToolRegistry, PermissionPolicy, register_builtin_tools
from .goals import GoalManager, Goal
from .state import (save_state, load_state, save_state_to_store,
                    load_state_from_store)
from .planner import LLMPlanner
from .scheduler import Scheduler
from .autonomous import AutonomousThoughtEngine
from .humanize import HumanizeEngine
from .meme_tool import register_meme_tool
from .personality.seed import Seed, SeedBank
from .personality.values import ValueSystem
from .personality.relationship import RelationshipGraph
from .personality.self_model import SelfModel
from .personality.identity import Identity
from .learning import LearningExtractor

logger = logging.getLogger("superbrain.agent")


@dataclass
class AgentConfig:
    name: str = "超脑"
    system_prompt: str = "你是「超脑」，一个带内在需求与情绪的自主智能体。用中文回答。"
    max_iterations: int = 10
    enable_memory: bool = True
    enable_tuning: bool = True
    enable_learning: bool = True   # 每轮对话后自动抽取种子/关系/事实
    max_context_tokens: int = 8000   # 上下文 token 预算（防无限增长）
    history_budget: int = 3000       # 对话历史 token 预算
    autosave: bool = True            # 自动保存（每 N 轮，防忘记 save 导致失忆）
    autosave_interval: int = 10      # 每 N 轮自动保存一次
    artifact_threshold: int = 2000   # 工具输出超过此字符数则 artifact 化（TokenPilot）
    artifact_upgrade_hits: int = 3   # artifact 被访问此次数后恢复完整内容（Ingestion Gate）
    compress_threshold: int = 4000   # 超过此 token 触发旧对话→摘要压缩
    humanize_output: bool = False    # 对外表达人性化（情绪口语化/卖萌）；默认关保持核心库纯粹，学习/记忆仍用原始答复


DEFAULT_PROMPT = "你是「超脑」智能体，有内在需求、情绪和记忆，可自主行动。请用中文回答。"


class SuperBrainAgent:
    def __init__(self, llm: LLMProvider, store: Optional[MemoryStore] = None,
                 config: Optional[AgentConfig] = None) -> None:
        self.config = config or AgentConfig()
        self.llm = llm
        self.store = store or MemoryStore()
        self.needs = NeedDriveSystem()
        self.emotion = EmotionGradient()
        self.neurochem = NeuroChemistry()
        self.meta = Metacognition()
        self.tuner = SelfTuner() if self.config.enable_tuning else None
        self._embedder = HashingEmbedder()
        # HashingEmbedder 输出已归一化 → 向量检索用点积快路径
        self.store.normalized = True
        self.distiller = Distiller()
        self.dreamer = DreamEngine(self.store, self.distiller)
        self.tools = ToolRegistry()
        self.permissions = PermissionPolicy()
        register_builtin_tools(self.tools)
        self.goals = GoalManager()
        self.planner = LLMPlanner(llm)
        self.scheduler = Scheduler()
        self.concept_extractor = ConceptExtractor(llm)
        self.concept_graph = ConceptGraph(self.store)
        self.seeds = SeedBank()
        self.values = ValueSystem()
        self.relationships = RelationshipGraph()
        self.self_model = SelfModel(identity="超脑", capability=["对话", "记忆", "工具执行", "规划"])
        self.identity = Identity(name="超脑")
        self.learning = LearningExtractor(llm) if self.config.enable_learning else None
        self.working = WorkingMemory()
        self.event_log = EventLog()
        self.schema_engine = SchemaEngine()      # PISA 三模态演化
        self.gwt = GlobalWorkspace(self._gwt_controller)  # 全局工作空间
        self._register_gwt_modules()
        self.attention = AttentionEngine()  # 注意力/显著性引擎
        self.autonomous = AutonomousThoughtEngine()  # 自主思考引擎
        self.humanize = HumanizeEngine()      # 人性化表达引擎
        register_meme_tool(self.tools)        # 表情包搜索工具
        self._active_rel = None  # 当前对话对象的关系（person_id 时）
        self._conversation: List[Dict[str, str]] = []
        self._compressed_summary: str = ""   # 旧对话的滚动摘要
        self._last_compress = 0.0
        self._last_message: str = ""   # 最近一条消息（GWT 种子模块用）
        self._artifacts: Dict[str, str] = {}  # 工具输出 artifact 存储（TokenPilot）
        self._artifact_access: Dict[str, int] = {}  # artifact 访问频率（Ingestion Gate）
        self._base_cache: str = ""  # 静态 base（身份+价值观）缓存，避免每轮重算
        self._stats = {"turns": 0}

    # ---------- 状态快照 ----------

    def state_snapshot(self) -> dict:
        dom, drive = self.needs.get_dominant_need()
        return {
            "needs": self.needs.get_profile(),
            "emotion": self.emotion.state.to_dict(),
            "neurochem": self.neurochem.to_dict(),
            "dominant_need": dom.value if dom else None,
            "dominant_drive": round(drive, 3),
            "memory_nodes": self.store.count_nodes(),
            "intrinsic_reward": round(self.emotion.mean_reward, 3),
            # 生命感板块可观察状态：自主消息积压 + 人性化可爱度
            "autonomous": {"pending_thoughts": self.autonomous.count},
            "humanize": {"cute_probability": self.humanize.cute_probability},
        }

    def _state_block(self) -> str:
        """精简内在状态（只注入关键值，省 token）。"""
        dom, drive = self.needs.get_dominant_need()
        e = self.emotion.state
        return (
            f"[状态] 主导需求={dom.value if dom else '无'} 驱动={round(drive,2)} "
            f"情绪={round(e.valence,2)}/{round(e.arousal,2)} "
            f"化学底色={round(self.neurochem.momentum(),2)} "
            f"记忆={self.store.count_nodes()}条"
        )

    def _base_prompt(self) -> str:
        """静态 base（system prompt + 身份 + 价值观），惰性缓存避免每轮重算。"""
        if self._base_cache:
            return self._base_cache
        parts = []
        anchor = self.identity.anchor_text()
        if anchor:
            parts.append(anchor)
        principle = self.values.principle_text()
        if principle:
            parts.append(f"核心原则：{principle}")
        base = (self.config.system_prompt or DEFAULT_PROMPT)
        if parts:
            base += "\n" + "\n".join(parts)
        self._base_cache = base
        return base

    # ---------- 记忆检索（受情绪影响） ----------

    def recall(self, query: str, k: int = 5) -> List[Tuple[MemoryNode, float, str]]:
        """检索记忆。情绪唤醒高时扩大召回 + 情绪偏好加权（Sentipolis 情绪-记忆耦合）。

        当前情绪(positive/negative)加权匹配的记忆：高兴时更容易想起高兴的经历。
        """
        if query is None:
            query = ""
        elif not isinstance(query, str):
            query = str(query)
        if not isinstance(k, int) or k <= 0:
            k = 5  # 脏 k（如字符串）防御，避免切片崩
        vec = self._embed(query)
        hits = retrieval.search(self.store, vec, query, k=k)
        current_valence = self.emotion.state.valence  # -1..1
        # 情绪偏好：valence 匹配的记忆加分（同号），情绪唤醒高时扩大召回
        for i, (node, score, why) in enumerate(hits):
            sim = current_valence * node.valence
            boost = sim * 0.15  # 同号情绪的记忆轻微上扬
            hits[i] = (node, score + boost, f"{why}+感情")
        # 唤醒高时多召回一点（更愿意联想）
        eager_k = k + int(self.emotion.state.arousal * 2) if self.emotion.state.arousal > 0.6 else k
        return hits[:max(k, eager_k)]

    def remember(self, content: str, tags: Optional[List[str]] = None,
                 importance: float = 0.5, scope: str = "user",
                 tier: str = "recall") -> MemoryNode:
        """写入记忆。情绪唤醒/支配高时提高置信度（更重要，更值得记）。"""
        if content is None:
            content = ""
        elif not isinstance(content, str):
            content = str(content)
        conf = min(1.0, 0.5 + self.emotion.state.arousal * 0.3 + self.emotion.state.dominance * 0.2)
        node = MemoryNode(
            node_id=fingerprint(content)[:16],
            content=content,
            embedding=self._embed(content),
            tags=tags or [],
            confidence=conf,
            scope=scope,
            tier=tier,
            valence=self.emotion.state.valence,  # 情绪标签（Sentipolis 耦合）
        )
        self.store.add(node)
        # 满足确定性需求（获得了新信息）
        self.needs.satisfy(NeedType.CERTAINTY, 0.05)
        return node

    def _embed(self, text: str) -> List[float]:
        """用哈希嵌入器生成向量（blake2b 特征哈希，跨进程一致）。"""
        return self._embedder.embed(text)

    # ---------- 主循环 ----------

    def chat(self, message: str, person_id: Optional[str] = None) -> str:
        # 入口防御：空/None/非 str 消息不崩、不污染会话、不调 LLM
        if message is None:
            message = ""
        elif not isinstance(message, str):
            message = str(message)
        if not message.strip():
            return "嗯？（没有收到消息内容）"
        # 自主关系演化：和某人相处，信任/熟悉/依恋随交互自然成长，超脑自主重新定性（非设定、非绑定）
        self._active_rel = None
        if person_id:
            try:
                rel = self.relationships.get_or_create(person_id)
                rel.grow(familiarity_delta=0.02, trust_delta=0.008, attachment_delta=0.004)
                self._active_rel = rel
            except Exception:
                self._active_rel = None
        self._stats["turns"] += 1
        self._last_message = message
        self._conversation.append({"role": "user", "content": message})

        # 0. 记录事件日志（溯源基础）+ 工作记忆
        try:
            self.event_log.append("conversation", message, provenance="direct_observation")
            self.working.add(message, kind="event")
        except Exception:
            pass  # 记录失败不影响对话

        # 1. 感知：需求 + 情绪 tick + 神经化学
        try:
            self.needs.tick()
            sats = {nt.value: self.needs.needs[nt].current_level for nt in self.needs.needs}
            self.emotion.update(sats)
            self.neurochem.tick()  # 递质按半衰期清除（情绪动量）
            self.neurochem.observe(self.emotion.state.valence, self.emotion.state.arousal)
        except Exception:
            sats = {}  # 感知异常降级：不崩，继续

        # 2. 记忆检索（受情绪影响的联想）—— 极短消息跳过检索省性能
        if self.config.enable_memory and not self._is_trivial(message):
            try:
                recalled = self.recall(message)
                mem_block = self._format_memory(recalled)
                scale = analyze_memory_scale(recalled)
                guide = expression_guide(scale)
            except Exception:
                recalled, mem_block, guide = [], "", ""  # 检索异常降级
        else:
            recalled, mem_block, guide = [], "", ""

        # 注意力焦点（人脑选择性注意）：当前最该关注哪个维度
        try:
            dom, drive = self.needs.get_dominant_need()
            focus = self.attention.focus(
                valence=self.emotion.state.valence,
                arousal=self.emotion.state.arousal,
                dominant_need=dom.value if dom else "无",
                need_drive=drive,
                memory_hits=len(recalled),
                input_text=message,
            )
            att_block = attention_block(focus)
        except Exception:
            att_block = ""

        # 3. 组装 prompt（静态 base 用缓存，其余惰性注入）
        msgs = [{"role": "system", "content": self._base_prompt()}]
        msgs.append({"role": "system", "content": self._state_block()})
        # 主导种子：当前情境下影响行为的倾向
        try:
            dominant_seed = self.seeds.dominant(message)
            if dominant_seed:
                msgs.append({"role": "system",
                             "content": f"[行为倾向] {dominant_seed.content}（倾向：{dominant_seed.behavior_bias}）"})
        except Exception:
            pass
        # 自我叙事：过去/现在/将来的我
        narrative = self.self_model.narrative()
        if narrative:
            msgs.append({"role": "system", "content": f"[自我] {narrative}"})
        # 工作记忆：当前任务/未完成事项（短期，容量受限）
        wm = self.working.summary()
        if wm:
            msgs.append({"role": "system", "content": f"[工作记忆] {wm}"})
        if mem_block:
            msgs.append({"role": "system", "content": f"[相关记忆]\n{mem_block}"})
        if guide:
            msgs.append({"role": "system", "content": guide})
        if att_block:
            msgs.append({"role": "system", "content": att_block})
        # 自主关系定位：我对当前这个人的内在关系认知（超脑自主判断，非绑定标签）
        if self._active_rel is not None:
            rel = self._active_rel
            nick = f"，昵称「{rel.nickname}」" if rel.nickname else ""
            msgs.append({"role": "system", "content":
                f"[我对{rel.name or '对方'}的关系] 定位={rel.orientation} "
                f"(把握{rel.orientation_confidence:.2f})，依恋{rel.attachment:.2f}，"
                f"熟悉{rel.familiarity:.2f}{nick}。这是我相处中自主形成的判断。"})
        # 对话历史：按 token 预算截断（而非固定条数，避免无限增长）
        msgs.extend(self._recent_history())

        # 4. 行动：function-calling 闭环（LLM 决定调用工具 → 执行 → 回传）
        answer = self._run_tool_loop(msgs)

        # 5. 学习：情绪更新 + 记忆沉淀 + 自适应调参 + 自动抽取学习信号
        success = 1.0 if answer else 0.0
        self.emotion.update(sats, task_success=success)
        try:
            self.emotion.compute_intrinsic_reward()  # 记录本轮内在奖励，供 mean_reward/tuner 用
        except Exception:
            pass
        if self.config.enable_memory and answer:
            try:
                self._remember_interaction(message, answer)
            except Exception:
                pass  # 沉淀失败不影响返回
        # 自动抽取种子/关系/事实（事件→种子闭环，启发式预筛省 token）
        if self.learning and answer and self._should_learn(message):
            try:
                learned = self.learning.extract(message, answer)
                self._apply_learning(learned)
                # PISA schema 演化：新对话归类/修正/创建图式
                self.schema_engine.ingest(message)
            except Exception:
                pass  # 学习失败不影响返回

        # 元认知反思：本次回答质量如何，是否高估了
        try:
            self.meta.reflect(
                decision=message[:50],
                reasoning_quality=0.5 + success * 0.3,
                confidence=self.emotion.state.confidence,
                outcome=success,
            )
        except Exception:
            pass

        if self.tuner and self.tuner.should_tune():
            try:
                reward = self.emotion.mean_reward
                fitness = self.tuner.current_fitness(reward, success)
                proposal = self.tuner.propose()
                self.tuner.evaluate_and_apply(fitness, fitness + 0.01, proposal)
            except Exception:
                pass

        # 人性化对外表达（可选）：按当前情绪做口语化/卖萌包装，仅影响返回，不影响学习与记忆沉淀
        if self.config.humanize_output and answer:
            try:
                if self._active_rel is not None:
                    rel = self._active_rel
                    answer = self.humanize.humanize(
                        answer, self.emotion.state,
                        familiarity=rel.familiarity, nickname=rel.nickname)
                else:
                    answer = self.humanize.humanize(answer, self.emotion.state)
            except Exception:
                pass
        self._conversation.append({"role": "assistant", "content": answer})
        self._maybe_compress()  # 分层记忆：超预算时旧对话→摘要
        self._maybe_autosave()  # 自动保存（防忘记 save 导致失忆）
        return answer

    def _apply_learning(self, learned: dict) -> None:
        """把抽取的学习信号写入人格层（种子/关系/事实）。"""
        # 种子：经历 → 行为倾向（去重强化 + 置信度门槛）
        for s in learned.get("seeds", []) or []:
            self.seeds.add_or_reinforce(
                content=s.get("content", ""),
                triggers=[s["trigger"]] if s.get("trigger") else None,
                behavior_bias=s.get("bias", ""),
                valence=float(s.get("valence", 0.0)),
                confidence=0.6,
            )
        # 关系：对说话者的了解
        for rel in learned.get("relationships", []) or []:
            person = rel.get("person", "")
            note = rel.get("note", "")
            if person and note:
                self.relationships.note(person, note, source="inference", confidence=0.5)
        # 事实：值得记住的确凿事实
        for fact in learned.get("facts", []) or []:
            if isinstance(fact, str) and fact.strip():
                self.remember(fact, scope="user", tier="recall")

    def _run_tool_loop(self, msgs: List[Dict], max_steps: int = 5) -> str:
        """function-calling 闭环：循环直到模型给出最终回答或达到步数上限。

        协议：
        1. 带 tools 调用 LLM
        2. 若 finish_reason=="tool_calls"，逐个执行工具，结果以 role=tool 回传
        3. 重复，直到 stop 或无工具调用
        """
        tools = self.tools.openai_schemas() if self.tools.list() else None
        for _ in range(max_steps):
            try:
                resp = self.llm.chat(msgs, tools=tools)
            except Exception as e:
                logger.warning("LLM 调用失败: %s", e)
                return self._fallback_reply("LLM 暂时不可用")
            if resp.tool_calls:
                # 记录 assistant 的 tool_calls 消息
                msgs.append({
                    "role": "assistant", "content": resp.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.name, "arguments": tc.arguments}}
                        for tc in resp.tool_calls
                    ],
                })
                for tc in resp.tool_calls:
                    result = self._dispatch_tool(tc)
                    msgs.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "name": tc.name, "content": str(result),
                    })
                continue
            return resp.content or ""
        return resp.content or ""

    def _fallback_reply(self, reason: str) -> str:
        """LLM 失败时的降级回复（不崩会话）。"""
        return (f"[服务降级] {reason}。请稍后再试，或检查模型通道配置。"
                f"（当前需求：{self.needs.get_dominant_need()[0].value if self.needs.get_dominant_need()[0] else '无'}）")

    def _dispatch_tool(self, tc) -> str:
        """执行一次工具调用，带权限门禁 + 大输出 artifact 化（TokenPilot）。"""
        tool = self.tools.get(tc.name)
        if tool is None:
            return f"[错误] 未知工具 {tc.name}"
        args = tc.args_dict()
        if self.permissions.needs_approval(tool.name, tool.category, tool.side_effects):
            # 危险工具需批准：框架层面返回待批准标记，由上层决定
            return (f"[需批准] 工具 {tool.name} 是危险操作，"
                    f"需要用户批准后才能执行。参数：{json.dumps(args, ensure_ascii=False)[:200]}")
        try:
            result = tool.call(**args)
            result = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return f"[错误] 工具 {tc.name} 执行失败: {e}"
        # Ingestion-Aware Compaction：进上下文前先清洗结构噪声（TokenPilot）
        result = clean_tool_output(result)
        if not result:
            return "[已执行，无有效输出]"
        # TokenPilot：环境消息（工具输出）默认压缩，访问频率超阈值则恢复完整
        if len(result) > self.config.artifact_threshold:
            import hashlib
            h = hashlib.blake2b(result.encode("utf-8"), digest_size=8).hexdigest()
            self._artifacts[h] = result  # artifact 注册表 𝒜（content hash → 完整内容）
            self._artifact_access[h] = self._artifact_access.get(h, 0) + 1
            # Ingestion Gate 𝔾(m)：访问频率超阈值 → 恢复完整内容交付
            if self._artifact_access[h] >= self.config.artifact_upgrade_hits:
                return result  # 高频访问的 artifact 升级为完整内容
            summary = result[:200].replace("\n", " ")
            return (f"[artifact:{h}] 已存 artifact，摘要：{summary}..."
                    f"（需完整内容用 recall_artifact('{h}')）")
        return result

    def recall_artifact(self, h: str) -> str:
        """恢复 artifact 完整内容（工具大输出）。"""
        return self._artifacts.get(h, "[未找到该 artifact]")

    def dream(self, window_hours: float = 24.0) -> List[str]:
        """睡眠计算：回顾近期记忆，提炼教训写回经验库。"""
        if not isinstance(window_hours, (int, float)):
            window_hours = 24.0  # None/非数值防御
        return self.dreamer.dream(window_hours=window_hours)

    # ---------- 全局工作空间 GWT ----------

    def _register_gwt_modules(self) -> None:
        """注册认知子系统为竞争模块（情绪/记忆/目标/元认知/种子/神经化学）。"""
        self.gwt.register("情绪", self._gwt_emotion)
        self.gwt.register("记忆", self._gwt_memory)
        self.gwt.register("目标", self._gwt_goal)
        self.gwt.register("元认知", self._gwt_meta)
        self.gwt.register("种子", self._gwt_seed)

    def _gwt_emotion(self) -> dict:
        e = self.emotion.state
        # 情绪越强(偏离中性)紧迫度越高
        urgency = min(1.0, abs(e.valence) * 0.8 + e.arousal * 0.4)
        mood = "积极" if e.valence > 0.2 else "消极" if e.valence < -0.2 else "平静"
        return {"content": f"当前情绪{mood}（valence={round(e.valence,2)}, 唤醒={round(e.arousal,2)}）",
                "urgency": urgency, "salience": abs(e.valence)}

    def _gwt_memory(self) -> dict:
        # 记忆检索的显著度：主导种子或新记忆驱动
        n = self.store.count_nodes()
        return {"content": f"有 {n} 条长期记忆可用", "urgency": 0.3,
                "salience": 0.3 if n > 0 else 0.0}

    def _gwt_goal(self) -> dict:
        active = [g for g in self.goals._goals if g.status != "completed"]
        if not active:
            return {"content": "", "urgency": 0, "salience": 0}
        g = active[0]
        return {"content": f"当前目标：{g.description[:40]}",
                "urgency": 0.6, "salience": 0.8}

    def _gwt_meta(self) -> dict:
        m = self.meta.cautiousness if hasattr(self.meta, "cautiousness") else 0.5
        refls = len(getattr(self.meta, "_reflections", []))
        return {"content": f"元认知：谨慎度{m}, 反思{refls}次",
                "urgency": 0.3, "salience": 0.4}

    def _gwt_seed(self, context: str = "") -> dict:
        s = self.seeds.dominant(self._last_message or "")
        if not s:
            return {"content": "", "urgency": 0, "salience": 0}
        return {"content": f"倾向：{s.content[:40]}",
                "urgency": 0.5, "salience": 0.5 * s.effective_strength()}

    def _gwt_controller(self, workspace_text: str) -> str:
        """统一行动：工作区内容决定优先处理什么。"""
        if self.learning:
            return f"[GWT决策] 基于工作区：{workspace_text[:80]}"
        return workspace_text[:80]

    def gwt_act(self) -> Optional[str]:
        """执行一次全局竞争→广播→行动。"""
        self._last_message = self._last_message or ""
        return self.gwt.act()

    # ---------- 状态持久化 ----------

    def _session_snapshot(self) -> dict:
        """会话态快照：对话历史 + 滚动摘要 + 工作记忆 + 事件日志。"""
        return {
            "conversation": list(self._conversation),
            "summary": self._compressed_summary,
            "working": self.working.to_dict(),
            "event_log": self.event_log.to_dict(),
            "schemas": self.schema_engine.to_dict(),
            "autonomous": self.autonomous.to_dict(),
            "humanize": self.humanize.to_dict(),
            "gwt_winner": [b.module for b in self.gwt.history[-10:]],
        }

    def _session_restore(self, d: dict) -> None:
        """恢复会话态（对话/摘要/工作记忆/事件日志）。"""
        self._conversation = list(d.get("conversation", []))
        self._compressed_summary = d.get("summary", "")
        self.working = self.working.__class__.from_dict(d.get("working", {}))
        self.event_log = self.event_log.__class__.from_dict(d.get("event_log", {}))
        from .memory.pisa import SchemaEngine
        self.schema_engine = SchemaEngine.from_dict(d.get("schemas", {}))
        from .autonomous import AutonomousThoughtEngine
        try:
            self.autonomous = AutonomousThoughtEngine.from_dict(d.get("autonomous", {}))
        except Exception:
            self.autonomous = AutonomousThoughtEngine()
        from .humanize import HumanizeEngine
        try:
            self.humanize = HumanizeEngine.from_dict(d.get("humanize", {}))
        except Exception:
            self.humanize = HumanizeEngine()

    def save(self, path: Optional[str] = None) -> str:
        """持久化认知+人格+会话状态到 store（默认，一个 .db = 整个大脑）或 JSON 文件。"""
        sess = self._session_snapshot()
        if path:
            save_state(path, self.needs, self.emotion, self.distiller, self.goals,
                       seeds=self.seeds, values=self.values,
                       relationships=self.relationships, self_model=self.self_model,
                       identity=self.identity, neurochem=self.neurochem, metacog=self.meta,
                       session=sess)
            return path
        save_state_to_store(self.store, self.needs, self.emotion,
                            self.distiller, self.goals, seeds=self.seeds,
                            values=self.values, relationships=self.relationships,
                            self_model=self.self_model, identity=self.identity,
                            neurochem=self.neurochem, metacog=self.meta, session=sess)
        return self.store.path

    def load(self, path: Optional[str] = None) -> bool:
        """恢复认知+人格+会话状态（优先 store，其次 JSON 文件）。"""
        sess = {}
        if path:
            ok = load_state(path, self.needs, self.emotion, self.distiller, self.goals,
                            seeds=self.seeds, values=self.values,
                            relationships=self.relationships, self_model=self.self_model,
                            identity=self.identity, neurochem=self.neurochem, metacog=self.meta,
                            session=sess)
        else:
            ok = load_state_from_store(self.store, self.needs, self.emotion,
                                       self.distiller, self.goals, seeds=self.seeds,
                                       values=self.values, relationships=self.relationships,
                                       self_model=self.self_model, identity=self.identity,
                                       neurochem=self.neurochem, metacog=self.meta, session=sess)
        if ok and sess:
            self._session_restore(sess)
        return ok

    def enable_autopilot(self, dream_interval: float = 3600.0,
                         act_interval: float = 1800.0,
                         thought_interval: float = 900.0) -> None:
        """开启主动运行：定时睡眠计算（dream）+ 定时行动（act）。

        让 agent 从被动应答变为主动感知——定时回顾沉淀经验、定时按需求行动。
        """
        self.scheduler.add("dream", dream_interval, lambda: self.dream())
        self.scheduler.add("act", act_interval, lambda: self.act())
        self.scheduler.add("thought", thought_interval, self._tick_autonomous)
        self.scheduler.start()

    def _tick_autonomous(self) -> Optional[str]:
        """空闲触发自主思考：产生想法并显式入队，供上层 drain() 灌进对话。"""
        try:
            for thought in self.autonomous.generate(self.needs, self.emotion,
                                                    self.relationships):
                self.autonomous.enqueue(thought)
        except Exception:
            pass
        return None

    # ---------- 概念图 + 去重 ----------

    def index_concepts(self, limit: int = 20) -> int:
        """增量抽取概念建图（只处理未索引的新节点，省 token）。"""
        total = 0
        processed = 0
        for node in self.store.all_nodes():
            if node.kind == "entity":
                continue
            if self.store.is_concept_indexed(node.node_id):
                continue  # 已索引，跳过（增量）
            entities, relations = self.concept_extractor.extract(node.content)
            total += self.concept_graph.index_memory(node, entities, relations)
            processed += 1
            if processed >= limit:
                break
        return total

    def deduplicate(self, threshold: float = 0.85) -> int:
        """合并近似记忆，返回合并对数。"""
        return dedupe.deduplicate(self.store, threshold)

    def expand_context(self, node_id: str, hops: int = 1) -> List:
        """沿概念图扩展，找跨记忆关联。"""
        return self.concept_graph.expand(node_id, hops)

    # ---------- 人格：种子/价值观/关系 ----------

    def learn_seed(self, content: str, triggers: List[str] = None,
                   behavior_bias: str = "", valence: float = 0.0,
                   confidence: float = 0.5, source_event: str = "") -> Seed:
        """从经历沉淀一条倾向种子（事件→种子的闭环入口）。"""
        return self.seeds.add(content, triggers=triggers, behavior_bias=behavior_bias,
                              valence=valence, confidence=confidence,
                              source_event=source_event)

    def note_relationship(self, person_id: str, content: str,
                          source: str = "observation", confidence: float = 0.5) -> None:
        """记录关系记忆（对某人的长期了解）。"""
        self.relationships.note(person_id, content, source, confidence)

    def act(self, goal: Optional[Goal] = None) -> Optional[str]:
        """行动：从需求派生目标 → 拆解 → 用工具执行下一步。

        返回本次行动的结果描述，或 None（无目标/无行动）。
        """
        dom, drive = self.needs.get_dominant_need()
        if goal is None:
            goal = self.goals.derive_goal(dom, drive)
            if goal is None:
                return None
            # LLM 规划拆解（Plan-and-Execute），失败回退规则
            steps = self.planner.plan(goal, [t.name for t in self.tools.list()])
            self.goals.decompose(goal, steps)
        task = self.goals.next_task(goal)
        if task is None:
            return f"目标「{goal.description[:30]}」已完成"
        # 用工具执行（这里用 read_file 做演示性只读行动）
        # 真正的工具选择应由 LLM 决定，这里提供框架
        result = f"已推进任务：{task.description}"
        self.goals.complete_task(goal, task.id, result)
        self.needs.satisfy(dom, 0.1)  # 行动满足需求
        return result

    def _remember_interaction(self, message: str, answer: str) -> None:
        """智能沉淀对话：只记有实质价值的，避免废话/寒暄膨胀记忆库。

        规则：
        - 太短的寒暄（如"你好""在吗"）不记
        - 只记答案里含实质信息（长度够、非纯寒暄）的交互
        """
        msg_len = len(message.strip())
        ans_len = len(answer.strip())
        # 寒暄过滤：双方都太短，或纯打招呼
        greetings = ("你好", "在吗", "hi", "hello", "谢谢", "好的", "ok")
        if msg_len < 4 or ans_len < 10:
            return
        if message.strip().lower() in greetings:
            return
        self.remember(f"用户问：{message[:80]} → 我答：{answer[:150]}",
                      scope="session")

    def _is_trivial(self, message: str) -> bool:
        """极短/无实质消息（"好""嗯"）跳过记忆检索，省性能。"""
        m = message.strip()
        if len(m) <= 2:  # 1-2 字视为寒暄/确认
            return True
        if len(m) <= 6 and m in ("好的", "嗯嗯", "哦", "是的", "对", "OK", "ok", "谢谢"):
            return True
        return False

    def _should_learn(self, message: str) -> bool:
        """启发式预筛：消息是否含可学习信号（避免每轮都调 LLM 抽取，省 token）。

        当消息涉及偏好/需求/习惯/自述经历/重要事实时才触发学习。
        """
        if len(message.strip()) < 6:  # 太短不值得学
            return False
        signals = ("我", "我们", "喜欢", "讨厌", "偏好", "希望", "习惯",
                   "需要", "不要", "想要", "别", "最", "通常", "一直",
                   "总是", "觉得", "认为", "记得", "计划", "目标",
                   "家人", "朋友", "工作", "学习")
        return any(s in message for s in signals)

    def _recent_history(self) -> List[Dict[str, str]]:
        """注入历史：滚动摘要 + 最近原始消息（清洗结构噪声，防上下文污染）。"""
        out: List[Dict[str, str]] = []
        if self._compressed_summary:
            out.append({"role": "system",
                        "content": f"[过往摘要] {self._compressed_summary}"})
        budget = self.config.history_budget
        used = 0
        for m in reversed(self._conversation):
            t = estimate_tokens(m["content"])
            if used + t > budget:
                break
            # Ingestion-Aware：清洗历史消息（旧 tool 消息降级、噪声丢弃）
            role = m.get("role", "user")
            content = clean_history_message(m["content"], role)
            if content is None or is_noise(content):
                continue  # 纯噪声丢弃
            out.append({"role": role, "content": content})
            used += t
        return list(reversed(out))

    def _maybe_autosave(self) -> None:
        """自动保存：每 N 轮持久化一次，防止忘记手动 save 导致失忆。"""
        if not self.config.autosave:
            return
        if self._stats["turns"] % self.config.autosave_interval == 0:
            try:
                self.save()
            except Exception as e:  # 自动保存失败不应中断对话
                logger.warning("自动保存失败: %s", e)

    def _maybe_compress(self) -> None:
        """分层记忆：对话超预算时，把旧对话压成滚动摘要，只保留最近 N 条原始。

        参照 Hermes 的滚动摘要压缩：旧对话→LLM归纳成摘要，新对话→原始。
        避免所有对话全量上传，同时保留关键语义。
        """
        total = sum(estimate_tokens(m["content"]) for m in self._conversation)
        if total <= self.config.compress_threshold:
            return
        import time as _time
        if _time.time() - self._last_compress < 60:  # 1分钟节流
            return
        self._last_compress = _time.time()
        # 保留最近 N 条原始（默认 6 条），其余拿去压摘要
        keep = self._conversation[-6:]
        to_summarize = self._conversation[:-6]
        if not to_summarize:
            return
        convo_text = "\n".join(
            f"{'用户' if m['role']=='user' else '助手'}: {m['content'][:150]}"
            for m in to_summarize[-30:])
        try:
            resp = self.llm.chat([
                {"role": "system", "content":
                 "你是对话压缩器。把下面的历史对话压缩成一段简洁摘要，保留："
                 "用户偏好、关键事实、未完成任务、重要结论。用中文，150字内。"},
                {"role": "user", "content": convo_text},
            ], max_tokens=400)
            summary = (resp.content or "").strip()
            if summary:
                self._compressed_summary = summary
                self._conversation = keep
        except Exception:
            pass  # 压缩失败则保持原样，不阻塞

    def _format_memory(self, hits: List[Tuple[MemoryNode, float, str]],
                       max_chars: int = 800) -> str:
        """格式化记忆注入，带 token 预算（限制注入字符数，省 token）。"""
        if not hits:
            return ""
        lines = []
        budget = 0
        for node, score, why in hits[:5]:
            content = node.content[:120]
            when = fuzzy_time(node.created_at)
            line = f"- [{why}] ({when}) {content}"
            if budget + len(line) > max_chars:
                break
            lines.append(line)
            budget += len(line)
        return "\n".join(lines)

    def stats(self) -> dict:
        return dict(self._stats, **self.state_snapshot())

    def close(self) -> None:
        # 先停后台调度线程再关闭 store，避免线程访问已释放的 SQLite 连接（段错误）
        try:
            self.scheduler.stop()
            self.scheduler.join(timeout=1.0)
        except Exception:
            pass
        self.store.close()
