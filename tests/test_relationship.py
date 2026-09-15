"""超脑 自主关系定位测试：关系是相处出来的，不是设定出来的。

验证 Relationship 的自主定性机制：attachment(依恋)/orientation(关系定性)/confidence，
随交互 grow 演化、无绑定接口，持久化往返不丢。
"""

import unittest

from superbrain.core.personality.relationship import Relationship, RelationshipGraph


class TestRelationshipOrientation(unittest.TestCase):
    def test_default_unoriented(self):
        """新建关系未定型（stranger）：超脑还没在相处中决定成为对方的什么人。"""
        rel = Relationship()
        self.assertEqual(rel.orientation, "stranger")
        self.assertEqual(rel.attachment, 0.0)

    def test_growth_reevaluates(self):
        """随交互 grow，超脑自主重新定性关系。"""
        g = RelationshipGraph()
        g.grow("p1", familiarity_delta=0.3, trust_delta=0.1)
        self.assertEqual(g.get("p1").orientation, "friend")     # 熟悉+信任 → 朋友
        g.grow("p1", familiarity_delta=0.3, trust_delta=0.3, attachment_delta=0.6)
        self.assertEqual(g.get("p1").orientation, "lover")      # 深依恋+熟悉 → 想成为恋人

    def test_qualification_tiers(self):
        """自主定性的各档位（stranger/acquaintance/friend/close/lover）。"""
        r = Relationship(trust=0.1, familiarity=0.1)
        r.reevaluate(); self.assertEqual(r.orientation, "stranger")
        r.familiarity = 0.3; r.reevaluate(); self.assertEqual(r.orientation, "acquaintance")
        r.familiarity = 0.6; r.trust = 0.5; r.reevaluate(); self.assertEqual(r.orientation, "friend")
        r.familiarity = 0.8; r.trust = 0.7; r.attachment = 0.2; r.reevaluate()
        self.assertEqual(r.orientation, "close")
        r.attachment = 0.7; r.reevaluate(); self.assertEqual(r.orientation, "lover")

    def test_grow_clamps(self):
        """grow 增量 clamp 到 [0,1]，不越界。"""
        rel = Relationship()
        rel.grow(trust_delta=5.0, familiarity_delta=5.0, attachment_delta=5.0)
        self.assertEqual(rel.trust, 1.0)
        self.assertEqual(rel.familiarity, 1.0)
        self.assertEqual(rel.attachment, 1.0)

    def test_persistence_roundtrip(self):
        """关系定位随持久化往返不丢。"""
        g = RelationshipGraph()
        g.grow("p1", familiarity_delta=0.5, trust_delta=0.3, attachment_delta=0.4)
        g2 = RelationshipGraph.from_dict(g.to_dict())
        self.assertEqual(g2.orientations(), g.orientations())

    def test_orientations_observability(self):
        """orientations() 暴露超脑对每个人的自主关系定位（可观察，非绑定）。"""
        g = RelationshipGraph()
        g.grow("p1", familiarity_delta=0.2)
        o = g.orientations()
        self.assertIn("p1", o)
        self.assertIn("orientation", o["p1"])
        self.assertIn("attachment", o["p1"])
        self.assertIn("confidence", o["p1"])


if __name__ == "__main__":
    unittest.main()