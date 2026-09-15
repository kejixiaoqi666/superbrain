"""超脑 自我模型 + 内部/对外情绪分离测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.personality.self_model import SelfModel
from superbrain.core.personality.identity import Identity
from superbrain.core.cognition.emotion import EmotionGradient, EmotionalState, Expression


class TestIdentity(unittest.TestCase):
    def test_anchor(self):
        id_ = Identity(name="小凌", core_identity="持续存在的角色",
                       expression_style="简洁直接")
        a = id_.anchor_text()
        self.assertIn("你是小凌", a)
        self.assertIn("简洁直接", a)

    def test_temporal(self):
        id_ = Identity(past_self="曾经青涩", present_self="正在成长",
                       future_self="希望更强大")
        t = id_.temporal_text()
        self.assertIn("过去", t)
        self.assertIn("现在", t)
        self.assertIn("将来", t)

    def test_roundtrip(self):
        id_ = Identity(name="超脑", boundaries=["不泄露隐私"])
        d = id_.to_dict()
        id2 = Identity.from_dict(d)
        self.assertEqual(id2.name, "超脑")
        self.assertEqual(id2.boundaries, ["不泄露隐私"])


class TestSelfModel(unittest.TestCase):
    def test_narrative(self):
        sm = SelfModel(
            identity="小凌",
            continuity=["曾经害怕被打断"],
            current_goal="帮用户解决问题",
            next_intention="继续了解用户",
        )
        n = sm.narrative()
        self.assertIn("我是小凌", n)
        self.assertIn("现在", n)
        self.assertIn("将来", n)

    def test_roundtrip(self):
        sm = SelfModel(identity="超脑", capability=["对话", "记忆"], uncertainty=["不确定用户意图"])
        d = sm.to_dict()
        sm2 = SelfModel.from_dict(d)
        self.assertEqual(sm2.identity, "超脑")
        self.assertEqual(sm2.capability, ["对话", "记忆"])


class TestEmotionSeparation(unittest.TestCase):
    def test_extended_dims(self):
        e = EmotionGradient()
        e.state.certainty = 0.8
        e.state.safety = 0.3
        e.state.fatigue = 0.6
        d = e.state.to_dict()
        self.assertEqual(d["certainty"], 0.8)
        self.assertEqual(d["safety"], 0.3)
        self.assertEqual(d["fatigue"], 0.6)

    def test_expression_deviation(self):
        # 内部强撑，对外说"我没事"——内部≠对外
        e = EmotionGradient()
        e.state.valence = -0.7  # 内部其实不好
        e.expression = Expression(text="我没事", intensity=0.2, deviation=0.9, reason="不想让对方担心")
        self.assertEqual(e.expression.text, "我没事")
        self.assertGreater(e.expression.deviation, 0.5)  # 偏差大 = 强撑
        self.assertLess(e.state.valence, 0)  # 内部是负的


if __name__ == "__main__":
    unittest.main()
