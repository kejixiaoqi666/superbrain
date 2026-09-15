"""超脑 多尺度记忆表达层测试。"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.expression_guide import analyze_memory_scale, expression_guide
from superbrain.core.memory.node import MemoryNode


def _node(content, confidence=0.8, valence=0.0, age_h=0.0):
    n = MemoryNode(content=content, confidence=confidence, valence=valence)
    n.last_access = time.time() - age_h * 3600.0
    return n


class TestExpressionGuide(unittest.TestCase):
    def test_empty_hits(self):
        s = analyze_memory_scale([])
        self.assertEqual(s["familiarity"], 0.0)
        self.assertEqual(expression_guide(s), "")

    def test_high_confidence_assertive(self):
        hits = [(_node("deepseek偏好", confidence=0.9), 0.8, "向量")]
        s = analyze_memory_scale(hits)
        g = expression_guide(s)
        self.assertIn("确定", g)  # 高置信 → 断言

    def test_low_confidence_hedge(self):
        hits = [(_node("模糊记忆", confidence=0.3), 0.5, "向量")]
        s = analyze_memory_scale(hits)
        g = expression_guide(s)
        self.assertIn("保留", g)  # 低置信 → 保留

    def test_stale_freshness(self):
        hits = [(_node("很久以前", age_h=200.0), 0.7, "向量")]
        s = analyze_memory_scale(hits)
        g = expression_guide(s)
        self.assertIn("过去", g)  # 久远 → 区分过去的我

    def test_negative_valence(self):
        hits = [(_node("糟糕经历", valence=-0.8), 0.7, "向量")]
        s = analyze_memory_scale(hits)
        g = expression_guide(s)
        self.assertIn("克制", g)  # 消极 → 克制/共情

    def test_scale_fields(self):
        hits = [(_node("x", confidence=0.9, valence=0.5), 0.9, "向量"),
                (_node("y", confidence=0.7, valence=-0.3), 0.6, "关键词")]
        s = analyze_memory_scale(hits)
        for k in ("familiarity", "confidence", "freshness", "valence", "granularity"):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()
