"""超脑 稳定性测试：异常隔离 + 静态缓存 + 短消息跳过。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain import SuperBrain, SuperBrainAgent
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
        a.chat("嗯")  # 短消息不应崩
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


class TestLongSessionBounded(unittest.TestCase):
    """v1.22.1 长会话有界性：conversation(token 预算制压缩) 不无界增长，各结构不超限。

    修复前 `_maybe_compress` 在 LLM 不可用/失败时静默不截断，长会话 _conversation
    会无界增长（300 轮≈300 条）；修复后始终截断，条数远小于总轮数。
    """

    def _brain(self):
        db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        b = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        b._agent.config.enable_learning = True
        b._agent.config.autosave = False
        b._agent.config.enable_tuning = False
        b._agent.config.compress_threshold = 200
        return b

    def test_conversation_not_unbounded(self):
        b = self._brain()
        msgs = ["我想探索新技术", "谢谢帮忙", "有点焦虑", "记一下蓝色",
                "继续任务", "好久不见"] * 8
        for i in range(300):
            b._agent._last_compress = 0   # 绕过节流，确保压缩反复触发
            b.chat(msgs[i % len(msgs)], person_id="u1")
            if i % 50 == 0:
                b.tick()
        conv = len(b._agent._conversation)
        # 修复前会无界增长到≈300；token 预算制下应远小于总轮数
        self.assertLess(conv, 60, f"_conversation 无界增长到 {conv} 条")
        b.close()

    def test_bounded_structures_within_caps(self):
        b = self._brain()
        msgs = ["我想探索新技术", "谢谢帮忙", "有点焦虑"] * 6
        for i in range(120):
            b.chat(msgs[i % len(msgs)], person_id="u1")
        self.assertLessEqual(len(b._agent.emotion._need_history), 100)
        self.assertLessEqual(len(b._agent.emotion._reward_history), 200)
        self.assertLessEqual(len(b._agent.attention.history), 50)
        self.assertLessEqual(len(b._agent.meta._reflections), 100)
        b.close()


if __name__ == "__main__":
    unittest.main()