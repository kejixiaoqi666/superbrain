"""超脑 生命感板块集成测试：自主思考 / 人性化表达 / 表情包工具 的装配与落地验证。

覆盖三块新能力在与 SuperBrainAgent 集成后的真实行为：
- 引擎是否装配进 agent（autonomous/humanize/search_meme 工具）
- 自主思考能否基于关系/需求触发
- function-calling 工具调用（handler 签名与 Tool.call 的 **kwargs 匹配）
- 人性化表达按亲密度/昵称包装
- 自主消息队列随 save/load 持久化（重启不丢）
- autopilot 含 thought 周期任务
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain import SuperBrain
from superbrain.core.llm import LLMResponse
from superbrain.core.autonomous import AutonomousThought, AutonomousThoughtEngine, ThoughtType


class StubLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="好的", finish_reason="stop")


class TestLifelike(unittest.TestCase):
    def _brain(self, db=None):
        if db is None:
            db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        from superbrain.core.memory.store import MemoryStore
        b = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        b._agent.config.enable_learning = False
        b._agent.config.autosave = False
        b._agent.config.enable_tuning = False
        b._db = db
        return b

    def test_engine_assemble(self):
        """三块引擎装配进 agent，search_meme 工具已注册。"""
        b = self._brain()
        self.assertIsNotNone(b._agent.autonomous)
        self.assertIsNotNone(b._agent.humanize)
        tool = b._agent.tools.get("search_meme")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.category, "media")
        self.assertFalse(tool.requires_approval)
        b.close()

    def test_generate_thoughts_from_relationship(self):
        """关系久未互动且熟悉度高 → 触发想念（MISS）。"""
        b = self._brain()
        b._agent.relationships.get_or_create("p1")
        b._agent.relationships.set_trust("p1", 0.9)
        rel = b._agent.relationships.get("p1")
        rel.familiarity = 0.9
        rel.updated_at = 1000.0  # 很久未互动
        kinds = {t.type for t in b.generate_thoughts()}
        self.assertIn(ThoughtType.MISS.value, kinds)
        b.close()

    def test_drain_thoughts(self):
        """自主消息队列 drain 取出并清空。"""
        b = self._brain()
        b._agent.autonomous.enqueue(
            AutonomousThought("miss", "好久没联系了", 0.5, "测试", created_at=1))
        self.assertEqual(b._agent.autonomous.count, 1)
        thoughts = b.drain_thoughts()
        self.assertEqual(len(thoughts), 1)
        self.assertEqual(thoughts[0].content, "好久没联系了")
        self.assertEqual(b._agent.autonomous.count, 0)
        b.close()

    def test_humanize_with_nickname(self):
        """按亲密度/昵称生成口语化表达，亲密度高时融入昵称。"""
        b = self._brain()
        b._agent.relationships.get_or_create("u1")
        b._agent.relationships.set_nickname("u1", "小七")
        b._agent.relationships.get("u1").familiarity = 0.9
        t = b.humanize("吃饭了吗", person_id="u1")
        self.assertIn("小七", t)
        self.assertIn("吃饭了吗", t)
        # 无对象时退化为中性包装，仍返回字符串
        self.assertIsInstance(b.humanize("好的", person_id=None), str)
        b.close()

    def test_meme_tool_function_calling(self):
        """function-calling 真实路径：ToolRegistry.call → handler(**kwargs) 不崩（mock 网络隔离）。"""
        from unittest.mock import patch
        b = self._brain()
        # mock 网络离线 → 走本地降级，避免真实网络与模块级缓存污染其它测试
        with patch("superbrain.core.meme_tool.urllib.request.urlopen", side_effect=OSError()):
            result = b._agent.tools.call("search_meme", query="开心", limit=1)
        self.assertIsInstance(result, str)  # 返回 JSON 字符串
        import json
        parsed = json.loads(result)
        self.assertIn("url", parsed[0]) if parsed else None
        b.close()

    def test_autonomous_persistence(self):
        """自主消息队列随 save/load 持久化（重启不丢）。"""
        b = self._brain()
        b._agent.autonomous.enqueue(
            AutonomousThought("miss", "好久没联系", 0.5, "测试", created_at=1))
        b.save()
        # 模拟重启：清空内存队列再 load
        b._agent.autonomous = AutonomousThoughtEngine()
        self.assertEqual(b._agent.autonomous.count, 0)
        ok = b.load()
        self.assertTrue(ok)
        self.assertEqual(b._agent.autonomous.count, 1)
        b.close()

    def test_autopilot_includes_thought(self):
        """autopilot 周期任务含 thought（自主思考）。"""
        b = self._brain()
        b._agent.enable_autopilot(dream_interval=9999, act_interval=9999,
                                  thought_interval=9999)
        names = {j["name"] for j in b._agent.scheduler.list()}
        self.assertIn("thought", names)
        b._agent.scheduler.stop()
        b.close()

    def test_chat_humanize_output(self):
        """humanize_output=True 时 chat 回复经情绪人性化包装；默认关则裸回复。"""
        b = self._brain()
        raw = b.chat("你好")
        self.assertEqual(raw, "好的")  # 默认关，裸回复
        b._agent.config.humanize_output = True
        ans = b.chat("你好")
        self.assertTrue(ans.startswith("好的"))  # 原答案保留
        self.assertGreater(len(ans), len("好的"))  # 且被加了口语化后缀
        b.close()

    def test_chat_edge_inputs(self):
        """chat 对空/None/非str/超长消息健壮不崩（入口防御）。"""
        b = self._brain()
        for msg in [None, "", "  ", 123, ["x"], {"a": 1}, "好" * 10000]:
            r = b.chat(msg)
            self.assertIsInstance(r, str)
        b.close()

    def test_facade_edge_inputs(self):
        """remember/recall/dream/state 对空/None/非str健壮不崩（入口防御）。"""
        b = self._brain()
        b.remember(None); b.remember(""); b.remember(123)          # 不崩
        self.assertIsInstance(b.recall(None), list)
        self.assertIsInstance(b.recall(""), list)
        self.assertIsInstance(b.recall(123), list)
        self.assertIsInstance(b.dream(None), list)
        self.assertIsInstance(b.dream(0), list)
        self.assertIsInstance(b.state(), dict)
        b.close()

    def test_state_observability_no_side_effect(self):
        """state() 无副作用且暴露新引擎状态；chat 记录内在奖励。"""
        b = self._brain()
        n1 = len(b._agent.emotion._reward_history)
        b.state(); b.state()
        self.assertEqual(n1, len(b._agent.emotion._reward_history))  # 观测无副作用
        b.chat("你好")
        self.assertGreater(len(b._agent.emotion._reward_history), n1)  # 每轮记录 reward
        s = b.state()
        self.assertIn("autonomous", s)   # 暴露自主消息积压
        self.assertIn("humanize", s)     # 暴露人性化可爱度
        b.close()

    def test_generate_is_pure_and_drain_consumes(self):
        """generate 纯产生不入队；enqueue 后 drain 消费清空。"""
        b = self._brain()
        b._agent.relationships.get_or_create("p1")
        b._agent.relationships.set_trust("p1", 0.9)
        rel = b._agent.relationships.get("p1")
        rel.familiarity = 0.9
        rel.updated_at = 1000.0  # 久未互动 → 触发想念
        thoughts = b.generate_thoughts()
        self.assertTrue(thoughts)
        self.assertEqual(b._agent.autonomous.count, 0)  # 纯产生不入队
        for t in thoughts:
            b._agent.autonomous.enqueue(t)
        self.assertGreater(b._agent.autonomous.count, 0)
        b.drain_thoughts()
        self.assertEqual(b._agent.autonomous.count, 0)  # drain 清空
        b.close()

    def test_tick_autonomous_enqueues(self):
        """_tick_autonomous 产生并显式入队（fresh 状态无冷却冲突）。"""
        b = self._brain()
        b._agent.relationships.get_or_create("p1")
        b._agent.relationships.set_trust("p1", 0.9)
        rel = b._agent.relationships.get("p1")
        rel.familiarity = 0.9
        rel.updated_at = 1000.0
        b._agent._tick_autonomous()
        self.assertGreater(b._agent.autonomous.count, 0)  # 已入队
        b.close()

    def test_chat_grows_relationship(self):
        """chat(person_id) 随相处自主演化关系，orientations() 可观察（非绑定）。"""
        b = self._brain()
        for _ in range(5):
            b.chat("今天过得怎么样", person_id="p1")
        o = b.orientations()
        self.assertIn("p1", o)
        self.assertGreater(o["p1"]["familiarity"], 0.0)  # 相处过 → 熟悉增长
        # 未传 person_id 不凭空创建关系
        self.assertEqual(set(b.orientations().keys()), {"p1"})
        b.close()

    def test_relationship_persists(self):
        """关系随 save/load 持久化（超脑记住和谁处于什么自主关系）。"""
        db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        from superbrain.core.memory.store import MemoryStore
        b = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        b._agent.config.enable_learning = False
        b._agent.config.autosave = False
        b._agent.config.enable_tuning = False
        for _ in range(3):
            b.chat("嗨", person_id="u1")
        b.save()
        b2 = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        b2._agent.config.enable_learning = False
        b2._agent.config.autosave = False
        b2._agent.config.enable_tuning = False
        b2.load()
        self.assertIn("u1", b2.orientations())
        b.close(); b2.close()


if __name__ == "__main__":
    unittest.main()