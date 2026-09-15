"""超脑 MCP 对接层测试（v1.22.1）：工具注册清单 + 关键工具调用不崩。"""
import os
import re
import sys
import tempfile
import unittest

# 隔离记忆库，避免污染真实 ~/.superbrain/brain.db
_os_patcher = object()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
_db = tempfile.mktemp(suffix=".db")


def setUpModule():
    os.environ["SUPERBRAIN_DB"] = _db


def tearDownModule():
    try:
        os.remove(_db)
    except FileNotFoundError:
        pass


class TestMCP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 重新导入，确保用隔离 db 装配
        import superbrain.server_mcp as m
        cls.m = m
        # 重新装配（reload 让 _brain 用隔离 db）
        m._brain = None
        m._get_brain()

    @staticmethod
    def _load(x):
        """MCP 工具返回 JSON 字符串，解析回对象；非字符串直接返回。"""
        import json
        return json.loads(x) if isinstance(x, str) else x

    def test_tool_registry(self):
        """注册工具清单：应含本轮全部工具，MCP 工具数 21。"""
        path = os.path.join(os.path.dirname(__file__), "..", "src",
                            "superbrain", "server_mcp.py")
        with open(path) as f:
            src = f.read()
        fns = re.findall(r"@mcp\.tool\(\)\n\s*def (\w+)", src)
        self.assertGreaterEqual(len(fns), 21)
        for t in ("brain_chat", "memory_remember", "memory_recall", "get_state",
                  "generate_thoughts", "drain_thoughts", "humanize", "search_meme",
                  "personality_profile", "set_personality", "superbrain_tick",
                  "personality_mode", "set_personality_mode", "apply_style",
                  "available_styles", "style_text", "generate_goals",
                  "autonomous_goals", "user_profile"):
            self.assertIn(t, fns)

    def test_superbrain_tick_shape(self):
        """superbrain_tick 返回含 thoughts/new_goals/reflected/absorbed 的 dict。"""
        out = self._load(self.m.superbrain_tick())
        self.assertIn("thoughts", out)
        self.assertIn("new_goals", out)
        self.assertIn("reflected", out)
        self.assertIn("absorbed", out)

    def test_style_and_mode(self):
        """apply_style 设风格并切 guided，personality_mode 反映当前模式。"""
        self.assertTrue(self._load(self.m.set_personality_mode("autonomous")))
        self.assertEqual(self._load(self.m.personality_mode()), "autonomous")
        applied = self._load(self.m.apply_style("可爱"))
        self.assertIsInstance(applied, list)
        self.assertEqual(self._load(self.m.personality_mode()), "guided")
        styles = self._load(self.m.available_styles())
        self.assertIn("可爱", styles)

    def test_memory_basic(self):
        """MCP 记忆读写通路。remember 返回 JSON 兼容的 node id 字符串。"""
        nid = self.m.memory_remember("MCP 测试记忆内容")
        self.assertIsInstance(nid, str)   # 修复：返回 node_id 而非 MemoryNode 对象
        self.assertTrue(nid)
        hits = self._load(self.m.memory_recall("MCP 测试", k=3))
        self.assertIsInstance(hits, list)

    def test_state_and_goals(self):
        """状态与自主目标通路。"""
        s = self._load(self.m.get_state())
        self.assertIn("needs", s)
        goals = self._load(self.m.generate_goals())
        self.assertIsInstance(goals, list)


if __name__ == "__main__":
    unittest.main()
