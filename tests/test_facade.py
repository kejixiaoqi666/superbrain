"""超脑 门面类测试：一行装配 + 统一接口。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain import SuperBrain
from superbrain.core.llm import LLMResponse


class StubLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="好的", finish_reason="stop")


class TestFacade(unittest.TestCase):
    def _brain(self):
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
        return b

    def test_one_line_assemble(self):
        """一行装配，全部模块可用。"""
        b = self._brain()
        # 核心模块都装配好了
        self.assertIsNotNone(b._agent.needs)
        self.assertIsNotNone(b._agent.emotion)
        self.assertIsNotNone(b._agent.memory if hasattr(b._agent, 'memory') else b._agent.store)
        self.assertIsNotNone(b._agent.identity)
        self.assertIsNotNone(b._agent.attention)
        b.close()

    def test_chat_works(self):
        b = self._brain()
        ans = b.chat("你好")
        self.assertIsInstance(ans, str)
        b.close()

    def test_remember_recall(self):
        b = self._brain()
        nid = b.remember("用户喜欢蓝色汽车")
        self.assertTrue(nid)
        hits = b.recall("用户喜欢什么")
        self.assertIsInstance(hits, list)
        b.close()

    def test_state_snapshot(self):
        b = self._brain()
        s = b.state()
        self.assertIn("needs", s)
        self.assertIn("emotion", s)
        b.close()

    def test_save_load(self):
        b = self._brain()
        b.remember("测试持久化记忆")
        b.save()
        b.close()

    def test_v122_framework_capabilities_facade(self):
        """v1.22.0 三框架能力门面方法可用。"""
        b = self._brain()
        # 人格维度
        prof = b.personality()
        self.assertEqual(len(prof), 5)
        self.assertTrue(b.set_personality("openness", 0.9))
        self.assertEqual(b.personality()["openness"]["value"], 0.9)
        # 自主目标生成
        b.generate_goals()
        self.assertIsInstance(b.autonomous_goals(), list)
        # 被动用户画像
        self.assertIsNone(b.user_profile("u1"))
        b.chat("聊聊 Python 和数据库", person_id="u1")
        up = b.user_profile("u1")
        self.assertIsNotNone(up)
        self.assertEqual(up["person_id"], "u1")
        b.close()

    def test_v122_save_load_roundtrip(self):
        """门面 save/load 往返：人格维度/自主目标/用户画像持久化不丢。"""
        db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        from superbrain.core.memory.store import MemoryStore
        b = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        b._agent.config.enable_learning = False
        b._agent.config.autosave = False
        b.chat("聊聊 Python 和数据库部署", person_id="u1")
        b.generate_goals()
        b.set_personality("extraversion", 0.85)   # 最后设定，避免 chat 被动观察干扰
        b.save()
        b.close()

        b2 = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        b2._agent.config.enable_learning = False
        b2._agent.config.autosave = False
        b2.load()
        self.assertEqual(b2.personality()["extraversion"]["value"], 0.85)
        up = b2.user_profile("u1")
        self.assertIsNotNone(up)
        self.assertGreater(up["interactions"], 0)
        b2.close()

    def test_v122_adopt_goals_closure(self):
        """意图→目标闭环：generate_goals 产出的自主目标可被采纳，且去重。"""
        b = self._brain()
        b.generate_goals()
        adopted = b.adopt_goals()
        self.assertGreaterEqual(len(adopted), 1)
        self.assertEqual(adopted[0]["source"], "autonomous")
        # 再采纳不重复（source_id 去重）
        again = b.adopt_goals()
        self.assertEqual(again, [])
        b.close()


class TestTick(unittest.TestCase):
    """v1.22.1 核心策略入口 tick()：一次推进，不自动发送（超脑是核心非智能体）。"""

    def _brain(self):
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
        return b

    def test_tick_shape(self):
        """tick 返回 dict，含 thoughts/new_goals/reflected 三个列表。"""
        b = self._brain()
        out = b.tick()
        self.assertIsInstance(out, dict)
        for k in ("thoughts", "new_goals", "reflected", "absorbed"):
            self.assertIsInstance(out[k], list)
        b.close()

    def test_tick_no_send(self):
        """tick 纯产生不入队：不自动发送，drain 队列始终空。"""
        b = self._brain()
        b.tick()
        b.tick()
        self.assertEqual(b.drain_thoughts(), [])
        b.close()

    def test_tick_after_interaction_no_crash(self):
        """相处 + 表达后 tick 正常推进，不崩、结构对。"""
        b = self._brain()
        b.chat("我想探索新东西，学习了解", person_id="u1")
        b.set_personality("openness", 0.9)
        b.humanize("好", "u1")
        out = b.tick()
        self.assertIsInstance(out["thoughts"], list)
        self.assertIsInstance(out["new_goals"], list)
        self.assertIsInstance(out["reflected"], list)
        b.close()

    def test_tick_new_goals_are_dicts(self):
        """新涌现的自主目标是可 JSON 序列化的 dict。"""
        b = self._brain()
        b._agent.auto_goals._goals.clear()
        out = b.tick()
        for g in out["new_goals"]:
            self.assertIsInstance(g, dict)
        b.close()


class TestAutonomyModeFacade(unittest.TestCase):
    """v1.22.1 进化模式开关的 facade 透传。"""

    def _brain(self):
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
        return b

    def test_default_and_set(self):
        b = self._brain()
        self.assertEqual(b.personality_mode(), "autonomous")
        self.assertTrue(b.set_personality_mode("guided"))
        self.assertEqual(b.personality_mode(), "guided")
        b.close()

    def test_apply_style_switches_guided(self):
        b = self._brain()
        applied = b.apply_style("可爱")
        self.assertIn("extraversion", applied)
        self.assertEqual(b.personality_mode(), "guided")
        self.assertEqual(b.personality()["extraversion"]["source"], "explicit")
        b.close()

    def test_guided_blocks_tick_absorb(self):
        """guided 下 tick 的画像升格不生效。"""
        b = self._brain()
        b.set_personality_mode("guided")
        b.chat("我想探索新技术，学习研究未知领域", person_id="u1")
        b._agent.user_profiles.get("u1").interactions = 12   # 造够相处
        out = b.tick()
        self.assertEqual(out["absorbed"], [])   # guided 下不升格
        self.assertEqual(b.personality()["openness"]["value"], 0.5)
        b.close()

    def test_available_styles(self):
        b = self._brain()
        styles = b.available_styles()
        self.assertIn("可爱", styles)
        self.assertIn("高冷", styles)
        b.close()


class TestPerUserStyle(unittest.TestCase):
    """v1.22.1 关系级风格：不同用户用不同表达倾向，全局人格不污染。"""

    def _brain(self):
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
        return b

    def test_set_and_get(self):
        b = self._brain()
        self.assertTrue(b.set_user_style("u_a", "可爱"))
        self.assertEqual(b.user_style("u_a"), "可爱")
        self.assertFalse(b.set_user_style("", "可爱"))     # 空 pid
        self.assertFalse(b.set_user_style("u_x", ""))      # 空风格
        b.close()

    def test_expression_overlay_no_pollution(self):
        """预置风格覆盖该用户表达人格，但全局人格不被污染。"""
        b = self._brain()
        b.set_user_style("u_a", "可爱")
        b.set_user_style("u_b", "高冷")
        a = b._agent.expression_personality("u_a")
        h = b._agent.expression_personality("u_b")
        self.assertGreater(a.get("extraversion").value, 0.6)   # 可爱→高外向
        self.assertLess(h.get("agreeableness").value, 0.4)     # 高冷→低宜人
        # 全局未污染
        g = b._agent.personality.get("extraversion")
        self.assertEqual(g.value, 0.5)
        self.assertEqual(g.source, "default")
        b.close()

    def test_custom_style_uses_global(self):
        """自定义风格(傲娇)：core 不预设映射，表达仍用全局人格。"""
        b = self._brain()
        b.set_user_style("u_c", "傲娇")
        self.assertEqual(b.user_style("u_c"), "傲娇")
        self.assertIs(b._agent.expression_personality("u_c"),
                      b._agent.personality)
        b.close()

    def test_no_style_uses_global(self):
        """未设风格的用户 → 直接用全局人格。"""
        b = self._brain()
        self.assertIs(b._agent.expression_personality("u_none"),
                      b._agent.personality)
        self.assertIs(b._agent.expression_personality(), b._agent.personality)
        b.close()

    def test_style_roundtrip(self):
        """per-user 风格持久化往返。"""
        from superbrain.core.user_profile import UserProfile
        p = UserProfile(person_id="u1")
        p.set_style("高冷")
        p2 = UserProfile.from_dict(p.to_dict())
        self.assertEqual(p2.style, "高冷")
        b = self._brain()
        b.set_user_style("u1", "温柔")
        s = b.state()
        self.assertIn("u1", str(s))   # 状态快照含用户
        b.close()


if __name__ == "__main__":
    unittest.main()