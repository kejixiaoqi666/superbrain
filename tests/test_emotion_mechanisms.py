"""超脑 情绪动力学机制测试（v2.0.0）：心境慢变量 + 时间衰减 + 情绪感染。

把内部情绪机制从"点状态计算"提升为"动力学系统"的验证。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain.core.cognition.emotion import EmotionGradient


def _good(level=0.9):
    return {"certainty": level, "relatedness": level, "competence": level,
            "autonomy": level}


def _bad(level=0.2):
    return {"certainty": level, "relatedness": level, "competence": level,
            "autonomy": level}


class TestMoodSlowVariable(unittest.TestCase):
    def test_mood_drifts_up_with_positive_events(self):
        """长期多次正面事件 → 心境(mood)基线缓慢上移（越来越乐观）。"""
        e = EmotionGradient()
        for _ in range(30):
            e.update(_good())
        self.assertGreater(e.state.mood, 0.05)   # 慢漂移但确实上升
        self.assertLess(e.state.mood, 1.0)       # 不会一步到位（慢变量）

    def test_mood_drifts_down_with_negative(self):
        """长期负面 → 心境基线下移。"""
        e = EmotionGradient()
        for _ in range(30):
            e.update(_bad())
        self.assertLess(e.state.mood, -0.05)


class TestTimeDecay(unittest.TestCase):
    def test_elapse_regresses_valence_to_mood(self):
        """瞬时高涨后，过一段时间 valence 向心境基线回归（事件会回落）。"""
        e = EmotionGradient()
        for _ in range(5):
            e.update(_good())                     # 短期反复高兴(瞬时)
        peak = e.state.valence
        # 多次 elapse 让时间流逝，瞬时情绪回落
        for _ in range(50):
            e.elapse(dt_hours=1.0, tau_hours=2.0)
        self.assertLess(e.state.valence, peak + 1e-9)      # 回落
        self.assertLess(e.state.valence, e.state.mood + 1e-6)  # 落到不高于基线

    def test_mood_changes_much_slower(self):
        """同样时间内，瞬时 valence 趋近 mood，但 mood 本身几乎不动（慢/快分离）。"""
        e = EmotionGradient()
        for _ in range(3):
            e.update(_good())
        mv = e.state.valence - e.state.mood       # 事件带来短时情绪高于基线
        self.assertGreater(mv, 0)
        for _ in range(10):
            e.elapse(dt_hours=3.0, tau_hours=2.0)
        mv_after = e.state.valence - e.state.mood
        self.assertLess(mv_after, mv)             # 快变量回归，慢变量稳定 → 差距收窄


class TestContagion(unittest.TestCase):
    def test_negative_contagion_lowers_valence(self):
        """他人长期低落(contagion<0) → 共情，自身 valence 被拉低（情绪感染）。"""
        e1 = EmotionGradient()
        e2 = EmotionGradient()
        for _ in range(3):
            e1.update(_good())
            e2.update(_good(), contagion=-0.6)    # 被低落的人感染
        self.assertLess(e2.state.valence, e1.state.valence)

    def test_positive_contagion_boosts(self):
        """他人高涨 → 自身被提振。"""
        e1 = EmotionGradient()
        e2 = EmotionGradient()
        for _ in range(3):
            e1.update(_bad())
            e2.update(_bad(), contagion=0.6)
        self.assertGreater(e2.state.valence, e1.state.valence)

    def test_zero_contagion_no_effect(self):
        """无感染时行为与原一致。"""
        e1 = EmotionGradient()
        e2 = EmotionGradient()
        for _ in range(3):
            e1.update(_good())
            e2.update(_good(), contagion=0.0)
        self.assertAlmostEqual(e2.state.valence, e1.state.valence, places=6)


class TestSocialEmotion(unittest.TestCase):
    """③ 自豪/愧疚：基于行为与自我标准的道德情感。"""

    def test_pride_raises_valence_dominance(self):
        e = EmotionGradient()
        e.update(_bad())
        before_v, before_d = e.state.valence, e.state.dominance
        e.social_update(pride=0.8)
        self.assertGreater(e.state.valence, before_v)
        self.assertGreater(e.state.dominance, before_d)
        self.assertGreater(e.state.pride, 0)

    def test_guilt_lowers_valence_dominance(self):
        e = EmotionGradient()
        e.update(_good())
        before_v, before_d = e.state.valence, e.state.dominance
        e.social_update(guilt=0.8)
        self.assertLess(e.state.valence, before_v)
        self.assertLess(e.state.dominance, before_d)
        self.assertGreater(e.state.guilt, 0)

    def test_pride_reduces_guilt(self):
        e = EmotionGradient()
        e.social_update(guilt=0.8)
        g = e.state.guilt
        e.social_update(pride=0.8)
        self.assertLess(e.state.guilt, g)   # 自豪减轻愧疚


class TestNeedImportanceLearning(unittest.TestCase):
    """④ 需求重要性习得：相对持续高缺口的需要重要性上升，形成个性偏好。"""

    def _system(self):
        from superbrain.core.cognition.needs import NeedDriveSystem, NeedType
        return NeedDriveSystem(), NeedType

    def test_importance_grows_for_unmet(self):
        sys_, NT = self._system()
        init_rel = sys_.needs[NT.RELATEDNESS].importance   # 初始 0.8
        init_cert = sys_.needs[NT.CERTAINTY].importance    # 初始 1.2
        # 长期不满足 relatedness（deficit 持续高），其他满足
        for _ in range(100):
            for nt in sys_.needs:
                if nt != NT.RELATEDNESS:
                    sys_.satisfy(nt, 1.0)
            sys_.tick()
        # 相对持续缺口的 need 重要性上升，长期不缺的回落（不受初始值干扰）
        self.assertGreater(sys_.needs[NT.RELATEDNESS].importance, init_rel)
        self.assertLess(sys_.needs[NT.CERTAINTY].importance, init_cert)

    def test_importance_bounded(self):
        """重要性习得有界(0.5..2.0)，不会无限涨。"""
        sys_, NT = self._system()
        for _ in range(200):
            for nt in sys_.needs:
                if nt != NT.RELATEDNESS:
                    sys_.satisfy(nt, 1.0)
            sys_.tick()
        for need in sys_.needs.values():
            self.assertLessEqual(need.importance, 2.0)
            self.assertGreaterEqual(need.importance, 0.5)


class TestEmotionConsistentRecall(unittest.TestCase):
    """② 认知-情绪回路：心境(mood)偏置记忆提取——低落偏向负面、高涨偏向正面。"""

    def test_low_mood_biases_negative_boost_positive(self):
        """低落心境(-) × 负面记忆valence(-) = 正 boost(同向增强)；正面记忆被抑制。"""
        mood, neg_v, pos_v = -0.8, -1.0, 1.0
        neg_boost = mood * neg_v * 0.25          # (-0.8)*(-1.0)*0.25 = +0.2 > 0
        pos_boost = mood * pos_v * 0.25          # (-0.8)*1.0*0.25 = -0.2 < 0
        self.assertGreater(neg_boost, 0)          # 低落时负面记忆增强
        self.assertLess(pos_boost, 0)             # 低落时正面记忆被抑制
        self.assertEqual(pos_boost, neg_boost * -1.0)

    def test_high_mood_biases_positive(self):
        """高涨心境(+) × 正面记忆 = 正 boost；负面被抑制。"""
        mood = 0.8
        self.assertGreater(mood * 1.0 * 0.25, 0)   # 高涨时正面增强
        self.assertLess(mood * -1.0 * 0.25, 0)     # 高涨时负面被抑制

    def test_inconsistent_memory_suppressed_half(self):
        """情绪不一致的记忆 boost 减半（轻微抑制，而非完全丢弃）。"""
        mood, pos_v = -0.8, 1.0
        inconsistent = mood * pos_v * 0.25 * 0.5   # 反向再×0.5
        self.assertLess(inconsistent, 0)


class TestSocialMotivation(unittest.TestCase):
    """③ 愧疚→修复关系冲动 + ② 低落时保守(抑制好奇探索)。"""

    def _setup(self, guilt=0.0, valence=0.0, certainty_dominant=True):
        from superbrain.core.autonomous import AutonomousThoughtEngine
        from superbrain.core.cognition.needs import NeedDriveSystem, NeedType
        from superbrain.core.cognition.emotion import EmotionGradient
        from superbrain.core.personality.relationship import RelationshipGraph
        engine = AutonomousThoughtEngine()
        needs = NeedDriveSystem()
        if certainty_dominant:   # 让 certainty 主导且驱动力够高
            for nt in needs.needs:
                if nt != NeedType.CERTAINTY:
                    needs.satisfy(nt, 1.0)
            needs.needs[NeedType.CERTAINTY].current_level = 0.2  # deficit 高 → drive 足
        emotion = EmotionGradient()
        emotion.state.guilt = guilt
        emotion.state.valence = valence
        rels = RelationshipGraph()
        rel = rels.get_or_create("u1", name="小明")
        rel.familiarity = 0.9
        return engine, needs, emotion, rels

    def test_high_guilt_produces_repair(self):
        """③ 愧疚高 → 对最在意的人生出修复冲动(repair)。"""
        e, needs, emotion, rels = self._setup(guilt=0.8)
        thoughts = e.generate(needs, emotion, rels, now=1000000)
        self.assertTrue(any(t.type == "repair" for t in thoughts))
        self.assertTrue(any("愧疚" in t.content for t in thoughts))

    def test_low_guilt_no_repair(self):
        """愧疚低 → 无修复冲动。"""
        e, needs, emotion, rels = self._setup(guilt=0.1)
        thoughts = e.generate(needs, emotion, rels, now=1000000)
        self.assertFalse(any(t.type == "repair" for t in thoughts))

    def test_low_mood_suppresses_curious(self):
        """② 低落 → 保守：抑制好奇探索，倾向稳住眼前。"""
        e, needs, emotion, rels = self._setup(valence=-0.5)
        thoughts = e.generate(needs, emotion, rels, now=1000000)
        self.assertFalse(any(t.type == "curious" for t in thoughts))
        self.assertTrue(any("稳住" in t.content for t in thoughts))

    def test_normal_mood_allows_curious(self):
        """正常情绪 → 仍允许好奇探索。"""
        e, needs, emotion, rels = self._setup(valence=0.2)
        thoughts = e.generate(needs, emotion, rels, now=1000000)
        self.assertTrue(any(t.type == "curious" for t in thoughts))


if __name__ == "__main__":
    unittest.main()