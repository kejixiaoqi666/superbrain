"""超脑 种子去重强化 + 置信度门槛测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.personality.seed import SeedBank


class TestSeedDedupe(unittest.TestCase):
    def test_add_or_reinforce_new(self):
        b = SeedBank()
        s = b.add_or_reinforce("遇到不确定时先完整表达", triggers=["不确定"], confidence=0.7)
        self.assertIsNotNone(s)
        self.assertEqual(len(b._seeds), 1)

    def test_add_or_reinforce_similar(self):
        b = SeedBank()
        b.add_or_reinforce("遇到不确定时先完整表达", confidence=0.7)
        # 相似种子 → 强化而非新增（字符重叠高）
        b.add_or_reinforce("遇到不确定时先完整表达", confidence=0.7)
        self.assertEqual(len(b._seeds), 1)  # 仍是一条
        seed = list(b._seeds.values())[0]
        self.assertGreaterEqual(seed.reinforcement_count, 1)  # 被强化了

    def test_confidence_threshold(self):
        b = SeedBank()
        s = b.add_or_reinforce("低置信度倾向", confidence=0.1)  # 低于门槛
        self.assertIsNone(s)
        self.assertEqual(len(b._seeds), 0)


if __name__ == "__main__":
    unittest.main()
