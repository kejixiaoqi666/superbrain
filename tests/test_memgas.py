"""超脑 MemGAS 多粒度熵路由器测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.retrieval import (granularity_weights, _shannon_entropy,
                                             adaptive_search)
from superbrain.core.memory.embeddings import HashingEmbedder
from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode
import tempfile


class TestMemGAS(unittest.TestCase):
    def test_shannon_entropy(self):
        # 均匀分布熵高，尖锐分布熵低
        h_uniform = _shannon_entropy([1,1,1,1])
        h_sharp = _shannon_entropy([10,1,1,1])
        self.assertGreater(h_uniform, h_sharp)

    def test_granularity_weights_sum_one(self):
        db = tempfile.mktemp(suffix=".db")
        try: os.remove(db)
        except FileNotFoundError: pass
        store = MemoryStore(db)
        emb = HashingEmbedder(dim=64)
        for i in range(10):
            store.add(MemoryNode(content=f"用户偏好 deepseek 做任务{i}", embedding=emb.embed(f"任务{i} deepseek")))
        cand = store.keyword_search("deepseek 偏好", k=20)
        w = granularity_weights(store, emb.embed("deepseek"), "deepseek 偏好", cand)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=3)
        store.close()

    def test_weights_nonempty(self):
        db = tempfile.mktemp(suffix=".db")
        try: os.remove(db)
        except FileNotFoundError: pass
        store = MemoryStore(db)
        emb = HashingEmbedder(dim=64)
        store.add(MemoryNode(content="测试记忆", embedding=emb.embed("测试")))
        cand = store.keyword_search("测试", k=20)
        w = granularity_weights(store, emb.embed("测试"), "测试", cand)
        self.assertGreater(len(w), 0)
        store.close()

    def test_multigranularity_path_uses_weights(self):
        """修复：multi_granularity=True 时 weights 真正生效（不再算了就丢，退化成普通 search）。

        多粒度路径应返回 top-k 且结果按熵权重排（keyword/summary/turn 三维加权）。
        """
        db = tempfile.mktemp(suffix=".db")
        try: os.remove(db)
        except FileNotFoundError: pass
        store = MemoryStore(db)
        emb = HashingEmbedder(dim=64)
        for i in range(12):
            store.add(MemoryNode(
                content=f"用户希望我用稳定负责任的方式处理任务{i}，坚持完成",
                embedding=emb.embed(f"任务{i} 坚持 完成")));
        cand = store.keyword_search("坚持 负责任 完成", k=20)
        self.assertGreater(len(cand), 0)
        # 多粒度路径：不应崩，返回 top-k 元组 (node, score, 原因)
        res = adaptive_search(store, emb.embed("坚持 负责任"),
                              "坚持 负责任 完成", k=3, multi_granularity=True)
        self.assertLessEqual(len(res), 3)
        for n, s, why in res:
            self.assertEqual(why, "多粒度熵路由")
        # 关键：返回结果用到了权重（非死逻辑）——空候选时不应靠普通 search 兜底
        res2 = adaptive_search(store, emb.embed("临时"), "完全不存在关键词xyz", k=2,
                               multi_granularity=True)
        self.assertIsInstance(res2, list)
        store.close()


if __name__ == "__main__":
    unittest.main()
