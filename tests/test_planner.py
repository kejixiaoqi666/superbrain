"""超脑 LLM 规划器测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.planner import LLMPlanner
from superbrain.core.goals import Goal


class TestPlanner(unittest.TestCase):
    def test_parse_steps_json(self):
        content = '["步骤1", "步骤2", "步骤3"]'
        steps = LLMPlanner._parse_steps(content)
        self.assertEqual(steps, ["步骤1", "步骤2", "步骤3"])

    def test_parse_steps_markdown(self):
        content = '```json\n["a", "b"]\n```'
        steps = LLMPlanner._parse_steps(content)
        self.assertEqual(steps, ["a", "b"])

    def test_parse_steps_bad(self):
        self.assertEqual(LLMPlanner._parse_steps("不是JSON"), [])

    def test_plan_fallback(self):
        """LLM 失败时回退规则拆解。"""
        class BadLLM:
            def chat(self, messages, **kw):
                raise RuntimeError("fail")
        p = LLMPlanner(BadLLM())
        g = Goal(description="测试目标")
        steps = p.plan(g, ["read_file"])
        self.assertGreaterEqual(len(steps), 3)  # 回退至少3步


if __name__ == "__main__":
    unittest.main()
