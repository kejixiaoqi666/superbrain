"""超脑 稳定性测试：异常隔离 + 静态缓存 + 短消息跳过。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain import SuperBrainAgent
from superbrain.core.llm import LLMResponse
from superbrain.core.memory.store import MemoryStore


class CrashLLM:
    """LLM 崩溃时 chat 应优雅降级。"""
    def chat(self, messages, tools=None, **kw):
        raise RuntimeError("LLM 崩溃模拟")


class StubLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="好的", finish_reason="stop")


class TestStability(unittest.TestCase):
    def _agent(self, llm):
        db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        a = SuperBrainAgent(llm, store=MemoryStore(db))
        a.config.enable_learning = False
        a.config.autosave = False
        a.config.enable_tuning = False
        return a

    def test_llm_crash_degrades_not_crash(self):
        """LLM 崩溃时 chat 返回降级提示，不抛异常。"""
        a = self._agent(CrashLLM())
        ans = a.chat("你好")
        self.assertIn("服务降级", ans)
        a.close()

    def test_trivial_message_skips_recall(self):
        a = self._agent(StubLLM())
        self.assertTrue(a._is_trivial("嗯"))
        self.assertFalse(a._is_trivial("帮我查一下deepseek的评测"))
        ans = a.chat("嗯")  # 短消息不应崩
        a.close()

    def test_base_cache_persists(self):
        a = self._agent(StubLLM())
        a.chat("第一条")
        c1 = a._base_cache
        self.assertTrue(c1)  # 缓存已建立
        # 再取一次应命中缓存（同一对象）
        c2 = a._base_prompt()
        self.assertIs(c2, a._base_cache)  # 惰性缓存返回同一缓存字符串
        a.close()


if __name__ == "__main__":
    unittest.main()