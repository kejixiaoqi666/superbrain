"""超脑 v1.22.0 自主目标生成测试。"""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.autonomous_goals import (
    AutonomousGoalEngine, GoalHorizon,
)
from superbrain.core.personality.dimensions import PersonalityDimensions
from superbrain.core.goals import GoalManager


def _needs(typ, drive):
    return SimpleNamespace(get_dominant_need=lambda: (typ, drive))


def _rels(**kw):
    return SimpleNamespace(all=lambda: [SimpleNamespace(**kw)])


def _emotion(valence):
    return SimpleNamespace(state=SimpleNamespace(valence=valence))


class TestAutonomousGoalEngine(unittest.TestCase):
    def test_need_driven_goal(self):
        e = AutonomousGoalEngine()
        now = 1_000_000
        out = e.generate(_needs("CERTAINTY", 0.6), None, _rels(), now=now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].driven_by, "certainty")
        self.assertEqual(out[0].horizon, GoalHorizon.MEDIUM)

    def test_no_goal_when_drive_low(self):
        e = AutonomousGoalEngine()
        out = e.generate(_needs("CERTAINTY", 0.1), None, _rels(), now=1_000_000)
        self.assertEqual(out, [])

    def test_emotion_driven_rest(self):
        e = AutonomousGoalEngine()
        out = e.generate(_needs("ENERGY", 0.0), _emotion(-0.8), _rels(), now=1_000_000)
        driven = {g.driven_by for g in out}
        self.assertIn("emotion", driven)

    def test_relationship_driven(self):
        e = AutonomousGoalEngine()
        r = _rels(person_id="p", name="小明", attachment=0.6)
        out = e.generate(_needs("ENERGY", 0.0), None, r, now=1_000_000)
        self.assertTrue(any(g.driven_by == "relatedness" for g in out))

    def test_personality_driven(self):
        e = AutonomousGoalEngine()
        pd = PersonalityDimensions()
        pd.set("openness", 0.9, confidence=0.8)
        out = e.generate(_needs("ENERGY", 0.0), None, _rels(), personality=pd,
                         now=1_000_000)
        self.assertTrue(any(g.driven_by == "openness" for g in out))

    def test_personality_neutral_no_goal(self):
        """中性人格维度不触发（把握度 0）。"""
        e = AutonomousGoalEngine()
        pd = PersonalityDimensions()
        out = e.generate(_needs("ENERGY", 0.0), None, _rels(), personality=pd,
                         now=1_000_000)
        self.assertEqual(out, [])

    def test_cooldown_and_dedup(self):
        """同源冷却 + 同内容去重：不重复刷目标。"""
        e = AutonomousGoalEngine()
        now = 1_000_000
        e.generate(_needs("CERTAINTY", 0.6), None, _rels(), now=now)
        # 同一时刻重复生成 → 冷却期内 + 去重，不再新增
        again = e.generate(_needs("CERTAINTY", 0.6), None, _rels(), now=now + 1)
        self.assertEqual(again, [])
        self.assertEqual(len(e.summary()), 1)
        # 冷却期过后，同内容 active 目标仍去重
        later = e.generate(_needs("CERTAINTY", 0.6), None, _rels(), now=now + 99999)
        self.assertEqual(later, [])

    def test_lifecycle(self):
        e = AutonomousGoalEngine()
        now = 1_000_000
        out = e.generate(_needs("CERTAINTY", 0.6), None, _rels(), now=now)
        gid = out[0].id
        self.assertEqual(len(e.active()), 1)
        e.complete(gid)
        self.assertEqual(len(e.active()), 0)
        self.assertEqual(e.summary()[0]["status"], "completed")

    def test_bounded_capacity(self):
        e = AutonomousGoalEngine(max_goals=5)
        now = 1_000_000
        # 5 种不同需求各触发一次，再触发一个情绪目标，验证上限
        for typ in ("CERTAINTY", "COMPETENCE", "AUTONOMY", "RELATEDNESS", "ENERGY"):
            e.generate(_needs(typ, 0.6), None, _rels(), now=now)
        e.generate(_needs("ENERGY", 0.0), _emotion(-0.9), _rels(), now=now + 3600)
        self.assertLessEqual(len(e.summary()), 5)

    def test_roundtrip(self):
        e = AutonomousGoalEngine()
        e.generate(_needs("CERTAINTY", 0.6), None, _rels(), now=1_000_000)
        d = e.to_dict()
        e2 = AutonomousGoalEngine.from_dict(d)
        self.assertEqual(len(e2.summary()), 1)
        self.assertEqual(e2.summary()[0]["driven_by"], "certainty")

    def test_dirty_from_dict(self):
        e = AutonomousGoalEngine.from_dict({
            "goals": ["bad", {"content": "x"}],
            "last_generate": {"k": "notnum", "j": 5},
        })
        self.assertEqual(len(e.summary()), 1)     # 非 dict 项被跳过
        self.assertEqual(e._last_generate, {"j": 5})


class TestAdoptClosure(unittest.TestCase):
    """意图 → 目标闭环：自主目标被采纳进 GoalManager 去重推进。"""

    def _make(self):
        e = AutonomousGoalEngine()
        e.generate(_needs("CERTAINTY", 0.6), None, _rels(), now=1_000_000)
        return e

    def test_adopt_and_dedup(self):
        e = self._make()
        gm = GoalManager()
        ag = e.active()[0]
        g = gm.adopt_autonomous(ag)
        self.assertIsNotNone(g)
        self.assertEqual(g.source, "autonomous")
        self.assertEqual(g.source_id, ag.id)
        self.assertEqual(g.description, ag.content)
        # 去重：同一自主目标不重复采纳
        self.assertTrue(gm.has_source(ag.id))
        self.assertIsNone(gm.adopt_autonomous(ag))
        self.assertEqual(len(gm.summary()), 1)

    def test_adopt_none(self):
        gm = GoalManager()
        self.assertIsNone(gm.adopt_autonomous(None))
        self.assertIsNone(gm.adopt_autonomous(SimpleNamespace(id="", content="")))


if __name__ == "__main__":
    unittest.main()
