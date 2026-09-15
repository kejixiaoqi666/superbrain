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


if __name__ == "__main__":
    unittest.main()
