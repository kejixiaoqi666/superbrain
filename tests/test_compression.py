"""超脑 滚动摘要压缩测试。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.llm import estimate_tokens
from superbrain import SuperBrainAgent
from superbrain.core.memory.store import MemoryStore


class FakeCompressLLM:
    """模拟：摘要请求返回摘要，普通对话返回长回复。"""
    def chat(self, messages, tools=None, **kw):
        if "压缩器" in messages[0].get("content", ""):
            return type("R", (), {"content": "[摘要] 用户讨论了超脑项目的架构设计",
                                  "finish_reason": "stop", "tool_calls": None})()
        return type("R", (), {"content": "好的，我会详细分析超脑项目的整体架构、分层记忆和token优化方案。",
                              "finish_reason": "stop", "tool_calls": None})()


class TestCompression(unittest.TestCase):
    def test_summary_generated(self):
        db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        store = MemoryStore(db)
        agent = SuperBrainAgent(FakeCompressLLM(), store=store)
        agent.config.history_budget = 2000
        agent.config.compress_threshold = 1500
        long_msg = ("我一直在思考超脑这个项目的整体架构应该怎么设计才更合理，"
                    "特别是分层记忆系统如何和token成本优化结合，既保证记忆完整"
                    "又控制开销，帮我分析神经化学和元认知的整合方案")
        for _ in range(15):
            agent.chat(long_msg)
        self.assertTrue(agent._compressed_summary)  # 摘要生成了
        total = sum(estimate_tokens(m["content"]) for m in agent._conversation)
        self.assertLessEqual(total, agent.config.compress_threshold)  # token受控
        agent.close()


if __name__ == "__main__":
    unittest.main()