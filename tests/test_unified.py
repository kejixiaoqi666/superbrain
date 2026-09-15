"""超脑 统一持久化测试（一个 .db = 整个大脑）。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.cognition.needs import NeedDriveSystem, NeedType
from superbrain.core.cognition.emotion import EmotionGradient
from superbrain.core.memory.distill import Distiller
from superbrain.core.goals import GoalManager
from superbrain.core.memory.store import MemoryStore
from superbrain.core.state import save_state_to_store, load_state_from_store


class TestUnifiedPersistence(unittest.TestCase):
    def test_store_roundtrip(self):
        """认知状态存入 SQLite meta 表，一个 db 全包。"""
        db = tempfile.mktemp(suffix=".db")
        store = MemoryStore(db)

        needs = NeedDriveSystem()
        needs.satisfy(NeedType.COMPETENCE, 0.4)
        emotion = EmotionGradient()
        emotion.update({"certainty": 0.9})
        dist = Distiller()
        dist.distill_skill("技能A", "步骤", success=True)
        goals = GoalManager()
        goals.derive_goal(NeedType.CERTAINTY, 0.7)

        save_state_to_store(store, needs, emotion, dist, goals)

        # 模拟重启：同一 db 新 store + 新认知实例
        store2 = MemoryStore(db)  # 同一文件
        needs2 = NeedDriveSystem()
        emotion2 = EmotionGradient()
        dist2 = Distiller()
        goals2 = GoalManager()
        ok = load_state_from_store(store2, needs2, emotion2, dist2, goals2)

        self.assertTrue(ok)
        self.assertEqual(len(dist2.best_skills()), 1)
        self.assertEqual(len(goals2._goals), 1)

        store.close()
        store2.close()
        os.remove(db)


if __name__ == "__main__":
    unittest.main()
