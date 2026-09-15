"""超脑 SuperBrain 融合功能测试：Mem0/Letta/Zep/PowerMem。"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode, fingerprint
from superbrain.core.memory import retrieval, heat, embeddings, distill, dream


class TestScopeTier(unittest.TestCase):
    """Mem0 作用域 + Letta 分层。"""

    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_scope(self):
        self.store.add(MemoryNode(content="用户偏好A", scope="user"))
        self.store.add(MemoryNode(content="会话临时B", scope="session"))
        self.assertEqual(len(self.store.by_scope("user")), 1)
        self.assertEqual(len(self.store.by_scope("session")), 1)

    def test_tier_promote(self):
        n = self.store.add(MemoryNode(content="核心记忆", tier="recall"))
        self.store.promote(n.node_id, "core")
        self.assertEqual(self.store.by_tier("core")[0].content, "核心记忆")


class TestZepTemporal(unittest.TestCase):
    """Zep 时序有效窗口。"""

    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_valid_window(self):
        now = time.time()
        # 已失效的记忆
        self.store.add(MemoryNode(content="旧方案", valid_until=now - 100))
        # 仍有效的记忆
        self.store.add(MemoryNode(content="当前方案", valid_until=now + 100000))
        valid = self.store.valid_nodes(now)
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].content, "当前方案")


class TestPowerMem(unittest.TestCase):
    """PowerMem 遗忘曲线 + 经验技能蒸馏。"""

    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_forgetting_curve(self):
        n = MemoryNode(content="测试", retention_strength=1.0)
        n.last_access = time.time() - 3600 * 24  # 24 小时前
        n.access_count = 0
        r = heat.retention(n)
        self.assertLess(r, 1.0)  # 遗忘后保留率 < 1

    def test_due_review(self):
        n = MemoryNode(content="测试", review_count=0)
        n.last_access = time.time() - 3600 * 2  # 2 小时前，超过 1h 间隔
        self.assertTrue(heat.due_for_review(n))

    def test_distill(self):
        d = distill.Distiller()
        d.record_experience("装node", "服务器", "成功", "先查版本")
        sk = d.distill_skill("装node", "apt install nodejs", success=True)
        self.assertGreater(sk.proficiency, 0.0)
        self.assertEqual(len(d.best_skills()), 1)


class TestLettaDream(unittest.TestCase):
    """Letta 睡眠计算。"""

    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_dream(self):
        self.store.add(MemoryNode(content="以后要注意备份数据库"))
        d = distill.Distiller()
        de = dream.DreamEngine(self.store, d)
        lessons = de.dream()
        self.assertGreaterEqual(len(lessons), 1)


if __name__ == "__main__":
    unittest.main()
