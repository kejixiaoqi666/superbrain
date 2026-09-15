"""超脑 function-calling 闭环测试。"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.llm import LLMProvider, LLMResponse, ToolCall


class TestFunctionCalling(unittest.TestCase):
    def test_tool_call_args(self):
        tc = ToolCall(id="c1", name="read_file", arguments='{"path":"/etc/hostname"}')
        self.assertEqual(tc.name, "read_file")
        self.assertEqual(tc.args_dict()["path"], "/etc/hostname")

    def test_tool_call_bad_json(self):
        tc = ToolCall(id="c1", name="x", arguments="not json")
        self.assertEqual(tc.args_dict(), {})


class TestDispatch(unittest.TestCase):
    """工具分发 + 权限门禁（用假 LLM 模拟 tool_calls）。"""

    def setUp(self):
        from superbrain.core.agent import SuperBrainAgent
        # 假 LLM：第一次返回 tool_call，第二次返回最终回答
        class FakeLLM:
            def __init__(self):
                self.calls = 0
            def chat(self, messages, tools=None, **kw):
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        content="", finish_reason="tool_calls",
                        tool_calls=[ToolCall(id="c1", name="read_file",
                                             arguments='{"path":"/etc/hostname"}')],
                    )
                return LLMResponse(content="已读到文件", finish_reason="stop")
        import tempfile
        self.db = tempfile.mktemp(suffix=".db")
        from superbrain.core.memory.store import MemoryStore
        a = SuperBrainAgent(FakeLLM(), store=MemoryStore(self.db))
        a.config.enable_memory = False  # 避免测试写库
        self.agent = a

    def tearDown(self):
        self.agent.store.close()
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_tool_loop_executes(self):
        """工具闭环：模型调用 read_file，最终返回回答。"""
        r = self.agent.chat("读一下hostname")
        self.assertEqual(r, "已读到文件")

    def test_approval_gate(self):
        """危险工具需批准，不实际执行。"""
        from superbrain.core.agent import SuperBrainAgent
        class FakeLLM2:
            def __init__(self):
                self.calls = 0
            def chat(self, messages, tools=None, **kw):
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        content="", finish_reason="tool_calls",
                        tool_calls=[ToolCall(id="c1", name="exec",
                                             arguments='{"command":"rm -rf /"}')],
                    )
                # 第二次：从 tool 消息里取结果回传
                tool_msg = next(m["content"] for m in messages if m.get("role") == "tool")
                return LLMResponse(content=tool_msg, finish_reason="stop")
        import tempfile
        from superbrain.core.memory.store import MemoryStore
        db = tempfile.mktemp(suffix=".db")
        a = SuperBrainAgent(FakeLLM2(), store=MemoryStore(db))
        a.config.enable_memory = False
        r = a.chat("执行危险命令")
        self.assertIn("需批准", r)
        a.store.close()
        if os.path.exists(db):
            os.remove(db)


if __name__ == "__main__":
    unittest.main()
