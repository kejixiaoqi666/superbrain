"""超脑 增量概念索引测试（省 token）。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode
from superbrain.core.memory.concept import ConceptGraph


class TestIncrementalIndex(unittest.TestCase):
    def test_skip_indexed(self):
        """已索引节点不重复抽概念。"""
        db = tempfile.mktemp(suffix=".db")
        store = MemoryStore(db)
        g = ConceptGraph(store)
        n = store.add(MemoryNode(content="超脑用deepseek", embedding=[0.1] * 64))
        g.index_memory(n, ["超脑", "deepseek"], [("超脑", "使用", "deepseek")])
        # 有 entity 出边 → 已索引
        self.assertTrue(store.is_concept_indexed(n.node_id))
        store.close()
        os.remove(db)

    def test_not_indexed(self):
        db = tempfile.mktemp(suffix=".db")
        store = MemoryStore(db)
        n = store.add(MemoryNode(content="未索引的记忆", embedding=[0.1] * 64))
        self.assertFalse(store.is_concept_indexed(n.node_id))
        store.close()
        os.remove(db)


if __name__ == "__main__":
    unittest.main()
