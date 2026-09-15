"""超脑 遗忘-重激活测试（v1.22.1）：遗忘=降级不删除，提起(强相关)即重激活。"""
import os
import sys
import time
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.embeddings import HashingEmbedder
from superbrain.core.memory.node import MemoryNode
from superbrain.core.memory.consolidation import Consolidator
from superbrain.core.memory import retrieval as R


class TestForgetAndReactivate(unittest.TestCase):
    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(self.db)
        except FileNotFoundError:
            pass
        self.store = MemoryStore(self.db)
        self.emb = HashingEmbedder(dim=256)
        for i in range(20):
            self.store.add(MemoryNode(
                content=f"用户偏好 docker 部署 {i}",
                embedding=self.emb.embed(f"docker 部署 {i}")))
        self.old_id = self.store.add(MemoryNode(
            content="用户非常喜欢蓝莓口味",
            embedding=self.emb.embed("蓝莓"))).node_id

    def tearDown(self):
        self.store.close()
        try:
            os.remove(self.db)
        except FileNotFoundError:
            pass

    def _make_old(self):
        # 让老记忆看起来很久未访问（value 低 → 会被遗忘）
        self.store.conn.execute(
            "UPDATE nodes SET last_access=?, access_count=0 WHERE node_id=?",
            (time.time() - 400 * 24 * 3600, self.old_id))
        self.store._commit_if_autonomous()

    def test_forget_downgrades_not_deletes(self):
        """长期未访问 → 睡眠遗忘降级 archival，且物理行仍存在。"""
        self._make_old()
        Consolidator(self.store).sleep(forget_below=0.05)
        self.assertEqual(self.store.get(self.old_id).tier, "archival")
        self.assertIsNotNone(self.store.get(self.old_id))   # 物理未删

    def test_weak_query_does_not_recall(self):
        """弱相关查询（不提蓝莓）→ 想不起来，保持 archival。"""
        self._make_old()
        Consolidator(self.store).sleep(forget_below=0.05)
        hits = R.search(self.store, self.emb.embed("docker"), "docker", k=5)
        self.assertFalse(any(n.node_id == self.old_id for n, _, _ in hits))
        self.assertEqual(self.store.get(self.old_id).tier, "archival")

    def test_strong_recall_reactivates(self):
        """强相关提起（重新提蓝莓）→ 命中 → 自动重激活回 recall。"""
        self._make_old()
        Consolidator(self.store).sleep(forget_below=0.05)
        hits = R.search(self.store, self.emb.embed("蓝莓 口味"), "蓝莓 口味", k=5)
        self.assertTrue(any(n.node_id == self.old_id for n, _, _ in hits))
        self.assertEqual(self.store.get(self.old_id).tier, "recall")  # 提起来又活跃

    def test_active_memories_strengthened(self):
        """长期使用的记忆保持 recall，不被误降级。"""
        Consolidator(self.store).sleep(forget_below=0.05, max_items=100)
        for n in self.store.all_nodes():
            self.assertNotEqual(n.tier, "archival")   # 刚建的都活跃，不该降级


class TestSchemaMigration(unittest.TestCase):
    """v2.0.0 旧版库 schema 迁移：缺新列时自动 ALTER 补列，数据保留。"""

    def test_migrate_old_db(self):
        import sqlite3
        db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        # 模拟 v1.x 旧库：nodes 缺 scope/tier/valence 等列
        c = sqlite3.connect(db)
        c.executescript("""
        CREATE TABLE nodes (node_id TEXT PRIMARY KEY, content TEXT, embedding BLOB,
            tags TEXT, scene TEXT, confidence REAL, kind TEXT,
            created_at REAL, last_access REAL, access_count INTEGER);
        CREATE TABLE edges (src TEXT, dst TEXT, weight REAL, kind TEXT, evidence TEXT);
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE VIRTUAL TABLE nodes_fts USING fts5(content, node_id UNINDEXED, tokenize='trigram');
        """)
        c.execute("INSERT INTO nodes (node_id,content,embedding,created_at,last_access) "
                  "VALUES (?,?,?,?,?)", ("old1", "旧版记忆", b"", 1, 1))
        c.commit()
        c.close()
        # 新版 MemoryStore 打开 → 应迁移补列
        store = MemoryStore(db)
        cols = {r[1] for r in store.conn.execute("PRAGMA table_info(nodes)")}
        for col in ("scope", "tier", "valence", "valid_from", "valid_until",
                    "retention_strength", "review_count"):
            self.assertIn(col, cols)          # 新列已补
        self.assertEqual(store.get("old1").content, "旧版记忆")  # 旧数据保留
        store.add(MemoryNode(content="新记忆", embedding=[0.5] * 16))  # 新代码可写
        self.assertGreaterEqual(store.count_nodes(), 2)              # 可查
        store.close()
        try:
            os.remove(db)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    unittest.main()