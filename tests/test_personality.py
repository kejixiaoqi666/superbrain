"""超脑 人格层测试：种子 + 价值观 + 关系。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.personality.seed import SeedBank
from superbrain.core.personality.values import ValueSystem
from superbrain.core.personality.relationship import RelationshipGraph


class TestSeed(unittest.TestCase):
    def test_add_and_match(self):
        bank = SeedBank()
        bank.add("完整表达能获得耐心回应", triggers=["不安", "担心被打断"],
                 behavior_bias="完整表达", confidence=0.7)
        matched = bank.match("我有点不安，担心被打断")
        self.assertGreaterEqual(len(matched), 1)

    def test_reinforce(self):
        bank = SeedBank()
        s = bank.add("倾向A", confidence=0.5)
        old_strength = s.strength
        bank.reinforce(s.id, 0.2)
        self.assertGreater(s.strength, old_strength)

    def test_correct(self):
        bank = SeedBank()
        s = bank.add("旧判断", confidence=0.9)
        bank.correct(s.id, "新判断")
        self.assertEqual(s.content, "新判断")
        self.assertEqual(s.revision, 2)

    def test_revoke(self):
        bank = SeedBank()
        s = bank.add("错误种子")
        bank.revoke(s.id)
        self.assertEqual(len(bank.all()), 0)


class TestValues(unittest.TestCase):
    def test_default_principles(self):
        vs = ValueSystem()
        self.assertGreaterEqual(len(vs.principles), 5)
        self.assertIn("不编造自己没有的经历", vs.principle_text())

    def test_preference(self):
        vs = ValueSystem()
        vs.add_preference("music", "古典", confidence=0.8)
        self.assertEqual(vs.get_preference("music").value, "古典")


class TestRelationship(unittest.TestCase):
    def test_note_and_trust(self):
        g = RelationshipGraph()
        g.note("user1", "对方喜欢聊技术", source="observation", confidence=0.8)
        g.set_trust("user1", 0.9)
        rel = g.get("user1")
        self.assertEqual(rel.trust, 0.9)
        self.assertEqual(len(rel.notes), 1)

    def test_boundary(self):
        g = RelationshipGraph()
        g.add_boundary("user1", "不喜欢被催")
        self.assertIn("不喜欢被催", g.get("user1").boundaries)


class TestPersistence(unittest.TestCase):
    def test_seed_roundtrip(self):
        bank = SeedBank()
        bank.add("种子X", triggers=["t1"], confidence=0.6)
        d = bank.to_dict()
        bank2 = SeedBank.from_dict(d)
        self.assertEqual(len(bank2.all()), 1)
        self.assertEqual(bank2.all()[0].content, "种子X")


if __name__ == "__main__":
    unittest.main()
