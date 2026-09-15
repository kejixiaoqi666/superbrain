"""超脑 概念抽取 + 记忆去重测试。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.concept import ConceptExtractor, ConceptGraph
from superbrain.core.memory import dedupe
from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode


class TestConceptExtract(unittest.TestCase):
    def test_parse(self):
        content = '{"entities":["deepseek","超脑"],"relations":[["超脑","使用","deepseek"]]}'
        entities, relations = ConceptExtractor._parse(content)
        self.assertEqual(entities, ["deepseek", "超脑"])
        self.assertEqual(relations, [("超脑", "使用", "deepseek")])

    def test_parse_bad(self):
        self.assertEqual(ConceptExtractor._parse("不是json"), ([], []))


class TestConceptGraph(unittest.TestCase):
    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_index_and_expand(self):
        g = ConceptGraph(self.store)
        n1 = self.store.add(MemoryNode(content="超脑用deepseek"))
        n2 = self.store.add(MemoryNode(content="deepseek是推理模型"))
        g.index_memory(n1, ["超脑", "deepseek"], [("超脑", "使用", "deepseek")])
        g.index_memory(n2, ["deepseek"], [])
        # 从 n1 扩展应能找到 n2（通过 shared 实体 deepseek）
        expanded = g.expand(n1.node_id, hops=2)
        contents = [n.content for n, _ in expanded]
        self.assertIn("deepseek是推理模型", contents)


class TestDedupe(unittest.TestCase):
    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_find_duplicates(self):
        v = [0.5] * 64
        self.store.add(MemoryNode(content="我喜欢用deepseek", embedding=v))
        self.store.add(MemoryNode(content="我喜欢用deepseek啊", embedding=v))
        pairs = dedupe.find_duplicates(self.store, threshold=0.5)
        self.assertGreaterEqual(len(pairs), 1)

    def test_merge(self):
        v = [0.5] * 64
        a = self.store.add(MemoryNode(content="我偏好使用deepseek模型", embedding=v))
        b = self.store.add(MemoryNode(content="我偏好使用deepseek这个模型", embedding=v))
        merged = dedupe.deduplicate(self.store, threshold=0.9)
        self.assertGreaterEqual(merged, 1)
        # 被取代后 superseded_by 能查到
        self.assertIsNotNone(self.store.superseded_by(b.node_id) or self.store.superseded_by(a.node_id))


if __name__ == "__main__":
    unittest.main()
