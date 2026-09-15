"""超脑 v1.22.0 被动用户画像测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.user_profile import UserProfileGraph, UserProfile


class TestUserProfile(unittest.TestCase):
    def test_observe_style(self):
        """长消息 → 话多，短消息 → 精简。"""
        p = UserProfile(person_id="u", name="小明")
        p.observe_message("你好")
        p.observe_message("在吗")
        self.assertLess(p.style_verbose, 0.0)     # 短消息 → 精简
        p2 = UserProfile(person_id="u2")
        p2.observe_message("我觉得这个方案有几个问题，第一是性能方面需要优化，"
                           "第二是接口设计可以更简洁，第三是文档还需要补充很多细节说明")
        self.assertGreater(p2.style_verbose, 0.0)

    def test_observe_mood(self):
        p = UserProfile(person_id="u")
        p.observe_message("我今天特别开心，事情很顺利！")
        before = p.mood_mean
        self.assertGreater(before, 0.0)
        p.observe_message("好难过，太焦虑了")
        self.assertLess(p.mood_mean, before)   # 负面消息 → 情绪基调下降

    def test_observe_topics(self):
        p = UserProfile(person_id="u")
        p.observe_message("今天研究了一下 Python 和数据库")
        p.observe_message("Python 的部署也很重要")
        self.assertIn("python", [t.lower() for t in p.topics])
        # 高频词排前
        self.assertEqual(p.topics[0].lower(), "python")

    def test_relationship_depth_grows(self):
        p = UserProfile(person_id="u")
        self.assertEqual(p.interactions, 0)
        p.observe_message("你好")
        p.observe_message("在吗")
        self.assertEqual(p.interactions, 2)
        self.assertGreater(p.relationship_depth, 0.0)
        self.assertLessEqual(p.relationship_depth, 1.0)

    def test_empty_message_ignored(self):
        p = UserProfile(person_id="u")
        p.observe_message("")
        p.observe_message(None)
        self.assertEqual(p.interactions, 0)

    def test_preferences_and_interests(self):
        p = UserProfile(person_id="u")
        p.add_preference("music", "古典", confidence=0.8)
        p.add_interest("机器学习", confidence=0.7)
        self.assertEqual(len(p.preferences), 1)
        self.assertEqual(len(p.interests), 1)

    def test_profile_text(self):
        p = UserProfile(person_id="u")
        self.assertEqual(p.profile_text(), "")    # 无实质内容 → 空
        p.observe_message("聊聊 Python 和数据库吧")
        p.observe_message("Python 部署也很关键")
        text = p.profile_text()
        self.assertIn("常聊", text)
        self.assertIn("python", text)

    def test_roundtrip(self):
        p = UserProfile(person_id="u", name="小明")
        p.observe_message("聊聊 Python 和数据库")
        p.add_preference("music", "古典", confidence=0.8)
        d = p.to_dict()
        p2 = UserProfile.from_dict(d)
        self.assertEqual(p2.person_id, "u")
        self.assertEqual(p2.interactions, 1)
        self.assertEqual(len(p2.preferences), 1)
        self.assertIn("python", [t.lower() for t in p2.topics])


class TestUserProfileGraph(unittest.TestCase):
    def test_observe_creates_profile(self):
        g = UserProfileGraph()
        self.assertIsNone(g.get("u1"))
        g.observe("u1", "你好", name="小明")
        self.assertIsNotNone(g.get("u1"))
        self.assertEqual(g.get("u1").name, "小明")

    def test_summary(self):
        g = UserProfileGraph()
        g.observe("u1", "聊聊 Python", name="小明")
        s = g.summary()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["person_id"], "u1")
        self.assertEqual(s[0]["interactions"], 1)

    def test_roundtrip(self):
        g = UserProfileGraph()
        g.observe("u1", "聊聊 Python 和数据库", name="小明")
        d = g.to_dict()
        g2 = UserProfileGraph.from_dict(d)
        self.assertIsNotNone(g2.get("u1"))
        self.assertEqual(g2.get("u1").name, "小明")
        self.assertEqual(g2.get("u1").interactions, 1)

    def test_dirty_from_dict(self):
        g = UserProfileGraph.from_dict({"profiles": {"u1": "bad"}})
        self.assertIsNotNone(g.get("u1"))       # 脏值 → 默认空画像，不崩
        g2 = UserProfileGraph.from_dict("not a dict")
        self.assertEqual(len(g2.all()), 0)


class TestDerivePersonality(unittest.TestCase):
    """v1.22.1 用户画像→人格三级联动（长期偏好→习得表达倾向）。"""

    def _profile_with_topics(self, texts):
        p = UserProfile(person_id="u")
        for t in texts:
            p.observe_message(t)
        return p

    def test_insufficient_interaction(self):
        """相处不够(<10次) → 不升格（防早期瞎猜）。"""
        p = self._profile_with_topics(["探索新东西"] * 5)
        self.assertEqual(p.derive_personality(), {})

    def test_sufficient_exploration_grows_openness(self):
        """长期探索类话题 → 习得开放性。"""
        texts = ["我想探索新技术，学习研究未知领域"] * 12
        p = self._profile_with_topics(texts)
        derived = p.derive_personality()
        self.assertIn("openness", derived)
        self.assertGreater(derived["openness"], 0.5)

    def test_low_mood_grows_neuroticism(self):
        """情绪长期低落 → 习得共情（神经质升）。"""
        texts = ["好难过，太焦虑了", "今天很累，很担心",
                 "最近不开心，情绪低落"] * 4   # 12 条 + 负面情绪
        p = self._profile_with_topics(texts)
        self.assertGreaterEqual(p.interactions, 10)
        derived = p.derive_personality()
        self.assertIn("neuroticism", derived)
        self.assertGreater(derived["neuroticism"], 0.5)

    def test_aggregate_takes_max(self):
        """多个用户画像 → 聚合取各维度最高。"""
        g = UserProfileGraph()
        a = UserProfile(person_id="a")
        b = UserProfile(person_id="b")
        for _ in range(12):
            a.observe_message("探索新东西学习了解")
            b.observe_message("探索新技术研究未知")
        g._profiles = {"a": a, "b": b}
        agg = g.aggregate_personality()
        self.assertIn("openness", agg)
        # 两个用户都提供 openness，取 max
        self.assertGreaterEqual(
            agg["openness"], max(a.derive_personality()["openness"],
                                 b.derive_personality()["openness"]) - 1e-9)


class TestSetFromUser(unittest.TestCase):
    """v1.22.1 PersonalityDimensions.set_from_user 升格人格。"""

    def test_lift_and_source(self):
        from superbrain.core.personality.dimensions import PersonalityDimensions
        pd = PersonalityDimensions()
        lifted = pd.set_from_user({"openness": 0.8})
        self.assertIn("openness", lifted)
        self.assertEqual(pd.get("openness").source, "derived")
        self.assertAlmostEqual(pd.get("openness").value, 0.8, places=6)

    def test_not_override_explicit(self):
        """用户显式 set() 的维度不被画像升格覆盖。"""
        from superbrain.core.personality.dimensions import PersonalityDimensions
        pd = PersonalityDimensions()
        pd.set("openness", 0.9)
        self.assertEqual(pd.set_from_user({"openness": 0.8}), [])
        self.assertEqual(pd.get("openness").source, "explicit")
        self.assertAlmostEqual(pd.get("openness").value, 0.9, places=6)

    def test_only_lift_higher(self):
        """低于当前值的维度不升格（只升不降）。"""
        from superbrain.core.personality.dimensions import PersonalityDimensions
        pd = PersonalityDimensions()
        pd.observe("openness", 0.5)   # 已有被动成长到 >0.5
        before = pd.get("openness").value
        self.assertEqual(pd.set_from_user({"openness": 0.51}), [])
        self.assertGreaterEqual(pd.get("openness").value, before)

    def test_empty_and_dirty(self):
        from superbrain.core.personality.dimensions import PersonalityDimensions
        pd = PersonalityDimensions()
        self.assertEqual(pd.set_from_user({}), [])
        self.assertEqual(pd.set_from_user(None), [])
        self.assertEqual(pd.set_from_user({"fake": 0.9, "openness": "bad"}), [])


if __name__ == "__main__":
    unittest.main()
