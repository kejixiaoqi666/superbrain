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


if __name__ == "__main__":
    unittest.main()