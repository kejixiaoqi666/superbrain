"""超脑 SuperBrain 单元测试。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode, fingerprint
from superbrain.core.memory import retrieval, heat
from superbrain.core.cognition.needs import NeedDriveSystem
from superbrain.core.cognition.emotion import EmotionGradient
from superbrain.core.cognition.self_tune import SelfTuner


class TestMemory(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = MemoryStore(self.path)

    def tearDown(self):
        self.store.close()
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_content_freeze(self):
        """内容冻结：重复写同一内容不新增节点。"""
        self.store.add(MemoryNode(content="超脑项目", embedding=[0.1] * 128))
        self.store.add(MemoryNode(content="超脑项目", embedding=[0.1] * 128))
        self.assertEqual(self.store.count_nodes(), 1)

    def test_fingerprint_stable(self):
        """指纹归一化：空白大小写不影响。"""
        self.assertEqual(fingerprint("Hello World"), fingerprint("hello   world"))

    def test_retrieval_multiroute(self):
        """三路检索能命中并返回路径。"""
        self.store.add(MemoryNode(content="PSI 需求驱动是超脑的认知内核", embedding=[0.5] * 128))
        hits = retrieval.search(self.store, [0.5] * 128, "PSI 需求")
        self.assertGreater(len(hits), 0)
        self.assertIn("向量", hits[0][2])

    def test_add_many(self):
        """批量写入：一个事务写入多个节点，且内容冻结去重。"""
        nodes = [MemoryNode(content=f"bulk{i}", embedding=[0.1] * 128) for i in range(100)]
        nodes.append(MemoryNode(content="bulk0", embedding=[0.1] * 128))  # 重复，应去重
        added = self.store.add_many(nodes)
        # 100 + 1重复 → 实际写入100个（重复去重）
        self.assertEqual(self.store.count_nodes(), 100)
        self.assertEqual(len(added), 101)  # 返回全部（含去重跳过的）

    def test_heat_order(self):
        """热度：最近访问+高频排前。"""
        a = self.store.add(MemoryNode(content="记忆A", embedding=[0.1] * 128))
        self.store.add(MemoryNode(content="记忆B", embedding=[0.1] * 128))
        self.store.touch(a.node_id)
        top = heat.preload_candidates(self.store, k=1)
        self.assertEqual(top[0].content, "记忆A")

    def test_supersede(self):
        """取代边：内容冻结下标记新记忆替代旧记忆。"""
        old = self.store.add(MemoryNode(content="旧方案用A", embedding=[0.1] * 128))
        new = self.store.add(MemoryNode(content="新方案用B", embedding=[0.1] * 128))
        self.store.supersede(old.node_id, new.node_id)
        self.assertEqual(self.store.superseded_by(old.node_id).content, "新方案用B")

    def test_watermark(self):
        """同步水位线幂等。"""
        self.store.set_watermark("device1", 5)
        self.assertEqual(self.store.get_watermark("device1"), 5)


class TestEmbedding(unittest.TestCase):
    def test_hashing_stable(self):
        """哈希嵌入跨进程一致（blake2b 而非内置 hash）。"""
        from superbrain.core.memory.embeddings import HashingEmbedder
        e = HashingEmbedder(dim=64)
        a = e.embed("超脑项目")
        b = e.embed("超脑项目")
        self.assertEqual(a, b)  # 确定性

    def test_embedder_identity(self):
        """嵌入器指纹可生成。"""
        from superbrain.core.memory.embeddings import HashingEmbedder, embedder_identity
        e = HashingEmbedder(dim=64)
        ident = embedder_identity(e)
        self.assertEqual(ident["dim"], 64)
        self.assertIn("fp", ident)


class TestImportance(unittest.TestCase):
    def test_is_important(self):
        from superbrain.core.memory.heat import is_important
        from superbrain.core.memory.node import MemoryNode
        hi = MemoryNode(content="重要", confidence=0.9)
        lo = MemoryNode(content="普通", confidence=0.3)
        self.assertTrue(is_important(hi))
        self.assertFalse(is_important(lo))


class TestCognition(unittest.TestCase):
    def test_need_drive(self):
        nd = NeedDriveSystem()
        nd.tick()
        dom, drive = nd.get_dominant_need()
        self.assertIsNotNone(dom)
        self.assertGreater(drive, 0)

    def test_emotion_smooth(self):
        em = EmotionGradient()
        s = em.update({"a": 0.8, "b": 0.8})
        self.assertGreaterEqual(s.valence, -1.0)
        self.assertLessEqual(s.valence, 1.0)

    def test_self_tune(self):
        tuner = SelfTuner(interval=1)
        before = 0.5
        proposal = tuner.propose()
        r = tuner.evaluate_and_apply(before, before + 0.2, proposal)
        self.assertTrue(r["accepted"])


if __name__ == "__main__":
    unittest.main()
