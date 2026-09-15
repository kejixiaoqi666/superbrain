"""超脑 状态持久化测试（自我连续性）。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.cognition.needs import NeedDriveSystem, NeedType
from superbrain.core.cognition.emotion import EmotionGradient
from superbrain.core.memory.distill import Distiller
from superbrain.core.goals import GoalManager
from superbrain.core.state import save_state, load_state
from superbrain.core.personality.dimensions import PersonalityDimensions
from superbrain.core.autonomous_goals import AutonomousGoalEngine
from superbrain.core.user_profile import UserProfileGraph


class TestStatePersistence(unittest.TestCase):
    def test_roundtrip(self):
        """保存再加载，认知状态不丢。"""
        tmp = tempfile.mktemp(suffix=".json")

        # 初始状态
        needs = NeedDriveSystem()
        needs.satisfy(NeedType.COMPETENCE, 0.3)
        emotion = EmotionGradient()
        emotion.update({"certainty": 0.8})
        dist = Distiller()
        dist.distill_skill("装node", "apt install", success=True)
        goals = GoalManager()
        goals.derive_goal(NeedType.CERTAINTY, 0.6)
        save_state(tmp, needs, emotion, dist, goals)

        # 新实例（模拟重启）
        needs2 = NeedDriveSystem()
        emotion2 = EmotionGradient()
        dist2 = Distiller()
        goals2 = GoalManager()
        ok = load_state(tmp, needs2, emotion2, dist2, goals2)

        self.assertTrue(ok)
        # 需求恢复
        self.assertGreater(
            needs2.needs[NeedType.COMPETENCE].current_level,
            needs2.needs[NeedType.COMPETENCE].current_level - 0.5,
        )
        # 技能恢复
        self.assertEqual(len(dist2.best_skills()), 1)
        # 目标恢复
        self.assertEqual(len(goals2._goals), 1)

        os.remove(tmp)

    def test_load_missing_returns_false(self):
        needs = NeedDriveSystem()
        emotion = EmotionGradient()
        dist = Distiller()
        goals = GoalManager()
        ok = load_state("/nonexistent/state.json", needs, emotion, dist, goals)
        self.assertFalse(ok)

    def test_v122_framework_capabilities_roundtrip(self):
        """v1.22.0 三框架能力（人格维度/自主目标/被动用户画像）持久化往返。"""
        tmp = tempfile.mktemp(suffix=".json")
        needs = NeedDriveSystem()
        emotion = EmotionGradient()
        dist = Distiller()
        goals = GoalManager()

        personality = PersonalityDimensions()
        personality.set("openness", 0.85, note="用户鼓励探索")
        personality.observe("conscientiousness", 0.1, note="坚持任务")
        auto_goals = AutonomousGoalEngine()
        auto_goals.generate(needs, emotion,
                            type("R", (), {"all": lambda s: []})(),
                            personality=personality, now=1_000_000)
        n_goals = len(auto_goals.summary())
        user_profiles = UserProfileGraph()
        user_profiles.observe("u1", "聊聊 Python 和数据库", name="小明")

        save_state(tmp, needs, emotion, dist, goals,
                   personality=personality, auto_goals=auto_goals,
                   user_profiles=user_profiles)

        p2 = PersonalityDimensions()
        g2 = AutonomousGoalEngine()
        up2 = UserProfileGraph()
        ok = load_state(tmp, needs, emotion, dist, goals,
                        personality=p2, auto_goals=g2, user_profiles=up2)
        self.assertTrue(ok)
        self.assertEqual(p2.get("openness").value, 0.85)
        self.assertEqual(p2.get("openness").source, "explicit")
        self.assertGreater(p2.get("conscientiousness").value, 0.5)
        self.assertEqual(len(g2.summary()), n_goals)
        driven = {g["driven_by"] for g in g2.summary()}
        self.assertIn("openness", driven)   # 人格维度驱动的目标也恢复
        self.assertIsNotNone(up2.get("u1"))
        self.assertEqual(up2.get("u1").name, "小明")

        os.remove(tmp)

    def test_v200_autonomy_mode_style_roundtrip(self):
        """v2.0.0 进化模式开关 + 自定义风格持久化往返（挖漏洞发现丢失 bug 的回归）。"""
        tmp = tempfile.mktemp(suffix=".json")
        needs, emotion, dist, goals = (NeedDriveSystem(), EmotionGradient(),
                                       Distiller(), GoalManager())
        personality = PersonalityDimensions()
        personality.apply_style("可爱")   # → guided + custom_style="可爱"
        save_state(tmp, needs, emotion, dist, goals, personality=personality)
        p2 = PersonalityDimensions()
        ok = load_state(tmp, needs, emotion, dist, goals, personality=p2)
        self.assertTrue(ok)
        self.assertEqual(p2.mode, "guided")        # 回归：修复前回到 autonomous
        self.assertEqual(p2.style_text, "可爱")     # 回归：修复前丢失为空
        os.remove(tmp)

    def test_load_nondict_json_returns_false(self):
        """损坏/合法但非 dict 的 JSON → 容错返回 False，不崩溃（挖漏洞发现）。"""
        tmp = tempfile.mktemp(suffix=".json")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write('"garbage"')       # 合法 JSON 但非 dict
        ok = load_state(tmp, NeedDriveSystem(), EmotionGradient(),
                        Distiller(), GoalManager())
        self.assertFalse(ok)           # 回归：修复前 AttributeError 崩溃
        os.remove(tmp)


if __name__ == "__main__":
    unittest.main()
