"""超脑 v1.22.0 人格维度显式化测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.personality.dimensions import (
    PersonalityDimensions, BIG_FIVE,
)


class TestPersonalityDimensions(unittest.TestCase):
    def test_default_neutral(self):
        """框架初始全中性(0.5)、把握度 0，不做预设。"""
        pd = PersonalityDimensions()
        self.assertEqual(len(pd.all()), len(BIG_FIVE))
        for t in pd.all():
            self.assertEqual(t.value, 0.5)
            self.assertEqual(t.confidence, 0.0)
            self.assertEqual(t.source, "default")

    def test_observe_grows_toward_extreme(self):
        """被动观测：渐进成长，有饱和（不越界、不一步到位）。"""
        pd = PersonalityDimensions()
        t = pd.observe("openness", 0.1, note="用户爱探索")
        self.assertIsNotNone(t)
        self.assertGreater(t.value, 0.5)
        self.assertLess(t.value, 1.0)          # 渐进，非一步到位
        self.assertEqual(t.source, "experience")
        self.assertGreater(t.confidence, 0.0)

    def test_observe_saturation(self):
        """接近极值更难再推（饱和），且 clamp 到 [0,1]。"""
        pd = PersonalityDimensions()
        for _ in range(100):
            pd.observe("openness", 1.0)
        self.assertLessEqual(pd.get("openness").value, 1.0)
        # 反向推动也应有效
        pd.observe("openness", -2.0)
        self.assertGreaterEqual(pd.get("openness").value, 0.0)

    def test_set_explicit(self):
        """显式设定：来源标记 explicit，把握度高。"""
        pd = PersonalityDimensions()
        t = pd.set("extraversion", 0.9, note="用户说你应该更外向")
        self.assertEqual(t.value, 0.9)
        self.assertEqual(t.source, "explicit")
        self.assertEqual(t.confidence, 0.8)

    def test_unknown_dimension_returns_none(self):
        pd = PersonalityDimensions()
        self.assertIsNone(pd.set("nonexistent", 0.9))
        self.assertIsNone(pd.observe("nonexistent", 0.1))

    def test_salient_and_profile_text(self):
        """显著维度才注入 prompt；中性维度不出现。"""
        pd = PersonalityDimensions()
        self.assertEqual(pd.profile_text(), "")     # 全中性 → 空
        pd.set("openness", 0.9)
        text = pd.profile_text()
        self.assertIn("开放性", text)
        self.assertNotIn("尽责性", text)           # 未设定的维度不出现

    def test_observations_bounded(self):
        """证据日志有界，不无限增长。"""
        pd = PersonalityDimensions()
        for i in range(120):
            pd.observe("openness", 0.01, note=f"obs{i}")
        self.assertLessEqual(len(pd.get("openness").observations), 50)

    def test_roundtrip(self):
        pd = PersonalityDimensions()
        pd.set("openness", 0.8, note="探索")
        pd.observe("conscientiousness", 0.1, note="坚持")
        d = pd.to_dict()
        pd2 = PersonalityDimensions.from_dict(d)
        self.assertEqual(pd2.get("openness").value, 0.8)
        self.assertEqual(pd2.get("openness").source, "explicit")
        self.assertGreater(pd2.get("conscientiousness").value, 0.5)

    def test_dirty_from_dict(self):
        """脏数据 from_dict 不崩。"""
        pd = PersonalityDimensions.from_dict({"traits": {"openness": "bad"}})
        self.assertEqual(len(pd.all()), len(BIG_FIVE))
        pd2 = PersonalityDimensions.from_dict("not a dict")
        self.assertEqual(len(pd2.all()), len(BIG_FIVE))


class TestObserveInteraction(unittest.TestCase):
    """v1.22.1 人格维度被动成长：从相处经历自动 observe。"""

    def test_exploration_grows_openness(self):
        pd = PersonalityDimensions()
        before = pd.get("openness").value
        touched = pd.observe_interaction("我想探索一些新东西，学习点不了解的")
        self.assertIn("openness", touched)
        self.assertGreater(pd.get("openness").value, before)

    def test_care_grows_agreeableness(self):
        pd = PersonalityDimensions()
        touched = pd.observe_interaction("谢谢，你真好，太体贴了")
        self.assertIn("agreeableness", touched)
        self.assertGreater(pd.get("agreeableness").value, 0.5)

    def test_low_mood_grows_neuroticism(self):
        pd = PersonalityDimensions()
        touched = pd.observe_interaction("最近好焦虑，太难过了")
        self.assertIn("neuroticism", touched)
        self.assertGreater(pd.get("neuroticism").value, 0.5)

    def test_empty_and_nonstr(self):
        pd = PersonalityDimensions()
        self.assertEqual(pd.observe_interaction(""), [])
        self.assertEqual(pd.observe_interaction(None), [])
        self.assertEqual(pd.observe_interaction(123), [])

    def test_converges_bounded(self):
        """长期反复观察：value 收敛到高位且不越界，confidence 增长到上限。"""
        pd = PersonalityDimensions()
        for _ in range(500):
            pd.observe_interaction("探索新事物，学习了解")
        self.assertGreater(pd.get("openness").value, 0.9)   # 收敛到高位
        self.assertLessEqual(pd.get("openness").value, 1.0)  # 不越界
        self.assertAlmostEqual(pd.get("openness").confidence, 1.0, places=6)
        self.assertEqual(pd.get("openness").source, "experience")

    def test_roundtrip_preserves_growth(self):
        """被动成长的人格维度持久化往返。"""
        pd = PersonalityDimensions()
        pd.observe_interaction("谢谢你真体贴")
        d = pd.to_dict()
        pd2 = PersonalityDimensions.from_dict(d)
        self.assertGreater(pd2.get("agreeableness").value, 0.5)
        self.assertEqual(pd2.get("agreeableness").source, "experience")


class TestReflect(unittest.TestCase):
    """v1.22.1 人格主动自省（被动吸收→主动内化）。"""

    def test_internalizes_mismatch(self):
        """言行差距大 → 朝近期行为内化 + 把握度增，来源标记 reflection。"""
        pd = PersonalityDimensions()
        for _ in range(50):
            pd.observe("openness", 0.1)   # experience 通道推到高位
        before = pd.get("openness").value
        self.assertGreater(before, 0.75)                 # 确认经验通道推到高位
        touched = pd.reflect({"openness": 0.5})          # 但近期行为中性
        self.assertIn("openness", touched)
        self.assertLess(pd.get("openness").value, before)  # 朝 0.5 回调
        self.assertEqual(pd.get("openness").source, "reflection")

    def test_close_no_touch(self):
        """行为与人格差距小 → 不动。"""
        pd = PersonalityDimensions()
        pd.set("openness", 0.6)
        self.assertEqual(pd.reflect({"openness": 0.5}), [])
        self.assertEqual(pd.get("openness").value, 0.6)

    def test_doubt_unexpressed_salient(self):
        """显著但近期无表现的维度 → 把握度轻微下调（自我怀疑）。"""
        pd = PersonalityDimensions()
        for _ in range(25):
            pd.observe("extraversion", 0.1)   # experience 通道推到显著+高把握
        before_conf = pd.get("extraversion").confidence
        self.assertGreater(before_conf, 0.5)
        touched = pd.reflect({"openness": 0.5})   # 近期只表现 openness
        self.assertIn("extraversion", touched)
        self.assertLess(pd.get("extraversion").confidence, before_conf)

    def test_empty_and_dirty(self):
        """空/脏输入防御：不崩、无副作用。"""
        pd = PersonalityDimensions()
        pd.set("openness", 0.9)
        self.assertEqual(pd.reflect(), [])
        self.assertEqual(pd.reflect(None), [])
        self.assertEqual(pd.reflect({"openness": "bad", "fake": 0.9}), [])
        self.assertEqual(pd.get("openness").value, 0.9)

    def test_roundtrip_preserves_reflection(self):
        """自省结果持久化往返。"""
        pd = PersonalityDimensions()
        for _ in range(50):
            pd.observe("openness", 0.1)
        before = pd.get("openness").value
        pd.reflect({"openness": 0.4})
        d = pd.to_dict()
        pd2 = PersonalityDimensions.from_dict(d)
        self.assertLess(pd2.get("openness").value, before)
        self.assertEqual(pd2.get("openness").source, "reflection")


class TestConflictResolution(unittest.TestCase):
    """v1.22.1 人格四通道冲突消解：explicit 是唯一硬锁定。"""

    def _high_explicit(self):
        pd = PersonalityDimensions()
        pd.set("openness", 0.9)   # 用户显式设定（explicit, conf 0.8）
        return pd

    def test_explicit_immune_to_observe(self):
        """explicit 维度不被被动观察(experience)修改。"""
        pd = self._high_explicit()
        before = pd.get("openness").value
        for _ in range(20):
            pd.observe("openness", 0.1)
        self.assertEqual(pd.get("openness").value, before)
        self.assertEqual(pd.get("openness").source, "explicit")

    def test_explicit_immune_to_observe_interaction(self):
        """explicit 维度不被相处观察触发。"""
        pd = self._high_explicit()
        touched = pd.observe_interaction("我想探索新东西，学习了解")
        self.assertNotIn("openness", touched)
        self.assertEqual(pd.get("openness").value, 0.9)

    def test_explicit_immune_to_reflect(self):
        """explicit 维度不被主动内化(reflection)修改 value 或把握度。"""
        pd = self._high_explicit()
        touched = pd.reflect({"openness": 0.4})   # 近期行为与显式设定矛盾
        self.assertNotIn("openness", touched)
        self.assertEqual(pd.get("openness").value, 0.9)
        self.assertEqual(pd.get("openness").confidence, 0.8)
        self.assertEqual(pd.get("openness").source, "explicit")

    def test_explicit_immune_to_set_from_user(self):
        """explicit 维度不被画像升格(derived)覆盖。"""
        pd = self._high_explicit()
        touched = pd.set_from_user({"openness": 0.8})
        self.assertNotIn("openness", touched)
        self.assertEqual(pd.get("openness").value, 0.9)
        self.assertEqual(pd.get("openness").source, "explicit")

    def test_re_set_overrides(self):
        """只有用户显式重新 set() 能改 explicit 维度。"""
        pd = self._high_explicit()
        pd.set("openness", 0.6)
        self.assertEqual(pd.get("openness").value, 0.6)
        self.assertEqual(pd.get("openness").source, "explicit")

    def test_derived_survives_reflect(self):
        """derived 维度可被 reflect 触碰（soft），但 explicit 永不。"""
        pd = PersonalityDimensions()
        pd.set_from_user({"openness": 0.8})   # → derived
        pd.reflect({"openness": 0.8})          # 行为一致，不动
        self.assertEqual(pd.get("openness").value, 0.8)


class TestAutonomyMode(unittest.TestCase):
    """v1.22.1 进化模式开关：autonomous(自主演化) / guided(用户主导)。"""

    def test_default_autonomous(self):
        pd = PersonalityDimensions()
        self.assertEqual(pd.mode, "autonomous")

    def test_set_mode(self):
        pd = PersonalityDimensions()
        self.assertTrue(pd.set_mode("guided"))
        self.assertEqual(pd.mode, "guided")
        self.assertTrue(pd.set_mode("autonomous"))
        self.assertFalse(pd.set_mode("bogus"))   # 非法值拒绝
        self.assertEqual(pd.mode, "autonomous")

    def test_guided_blocks_all_auto_channels(self):
        """guided 下四个自动通道全停，人格纹丝不动。"""
        pd = PersonalityDimensions()
        pd.set_mode("guided")
        pd.observe("openness", 0.5)                          # 被动观察
        pd.observe_interaction("我想探索新东西学习了解")       # 相处观察
        pd.reflect({"openness": 0.9})                        # 主动内化
        pd.set_from_user({"openness": 0.8})                  # 画像升格
        for name in ("openness", "conscientiousness", "extraversion",
                     "agreeableness", "neuroticism"):
            self.assertEqual(pd.get(name).value, 0.5, name)  # 全中性
            self.assertEqual(pd.get(name).source, "default", name)

    def test_guided_still_allows_user_set(self):
        """guided 下用户 set 仍生效（用户主导 = 只听用户的）。"""
        pd = PersonalityDimensions()
        pd.set_mode("guided")
        pd.set("openness", 0.9)
        self.assertEqual(pd.get("openness").value, 0.9)
        self.assertEqual(pd.get("openness").source, "explicit")

    def test_autonomous_mode_normal(self):
        """autonomous 下观察正常成长。"""
        pd = PersonalityDimensions()
        pd.observe("openness", 0.1)
        self.assertGreater(pd.get("openness").value, 0.5)

    def test_apply_style(self):
        """apply_style('可爱') 设定大五维度组合并自动切 guided。"""
        pd = PersonalityDimensions()
        applied = pd.apply_style("可爱")
        self.assertIn("extraversion", applied)
        self.assertGreater(pd.get("extraversion").value, 0.6)
        self.assertGreater(pd.get("agreeableness").value, 0.6)
        self.assertEqual(pd.get("extraversion").source, "explicit")
        self.assertEqual(pd.mode, "guided")   # 一句风格 = 用户主导

    def test_apply_style_custom_not_locked(self):
        """自定义风格（如傲娇）：不强套维度，但记录表达风格并切 guided（完全听用户）。"""
        pd = PersonalityDimensions()
        applied = pd.apply_style("傲娇")
        self.assertEqual(applied, [])            # 无预置映射 → 不强套维度
        self.assertEqual(pd.style_text, "傲娇")  # 但记录用户指令
        self.assertEqual(pd.mode, "guided")
        self.assertEqual(pd.get("extraversion").value, 0.5)   # 维度不动
        # 自动通道全停（custom 风格下也受 guided 保护）
        pd.observe("extraversion", 0.5)
        self.assertEqual(pd.get("extraversion").value, 0.5)

    def test_style_presets_available(self):
        """风格预设清单非空且含用户提到的可爱/冷静/高冷。"""
        from superbrain.core.personality.dimensions import _STYLE_PRESETS
        for s in ("可爱", "冷静", "高冷", "温柔"):
            self.assertIn(s, _STYLE_PRESETS)

    def test_mode_roundtrip(self):
        """进化模式开关 + 自定义风格持久化往返。"""
        pd = PersonalityDimensions()
        pd.apply_style("高冷")
        d = pd.to_dict()
        pd2 = PersonalityDimensions.from_dict(d)
        self.assertEqual(pd2.mode, "guided")
        self.assertEqual(pd2.get("agreeableness").source, "explicit")
        # 自定义风格往返
        pd3 = PersonalityDimensions()
        pd3.apply_style("傲娇")
        pd4 = PersonalityDimensions.from_dict(pd3.to_dict())
        self.assertEqual(pd4.style_text, "傲娇")
        self.assertEqual(pd4.mode, "guided")
        # 脏值回退
        pd5 = PersonalityDimensions.from_dict({"autonomy_mode": "bogus"})
        self.assertEqual(pd5.mode, "autonomous")


if __name__ == "__main__":
    unittest.main()
