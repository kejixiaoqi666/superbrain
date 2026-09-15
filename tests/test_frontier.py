"""超脑 前沿模块测试：GWT/PISA/情绪耦合/EG-MRSI。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.gwt import GlobalWorkspace
from superbrain.core.memory.pisa import SchemaEngine
from superbrain.core.cognition.self_tune import SelfTuner
from superbrain.core.memory.node import MemoryNode


class TestGWT(unittest.TestCase):
    def test_competition_broadcast(self):
        g = GlobalWorkspace(controller=lambda text: text)
        g.register("高紧迫", lambda: {"content": "紧急！", "urgency": 0.9, "salience": 0.8})
        g.register("低紧迫", lambda: {"content": "随便", "urgency": 0.1, "salience": 0.1})
        out = g.act()
        self.assertIn("紧急", out)  # 高紧迫胜出广播

    def test_no_module(self):
        g = GlobalWorkspace(controller=lambda t: t)
        self.assertIsNone(g.act())


class TestPISA(unittest.TestCase):
    def test_create_then_assimilate(self):
        se = SchemaEngine()
        m1, _, _ = se.ingest("用户偏好使用 deepseek 模型", "n1")
        self.assertEqual(m1, "create")
        m2, _, _ = se.ingest("用户偏好使用 deepseek 模型 编码", "n2")
        self.assertIn(m2, ("assimilate", "accommodate"))
        self.assertGreaterEqual(len(se.all()), 1)

    def test_roundtrip(self):
        se = SchemaEngine()
        se.ingest("机场节点需要配置 machine", "n1")
        d = se.to_dict()
        se2 = SchemaEngine.from_dict(d)
        self.assertEqual(len(se2.all()), len(se.all()))


class TestEGMRSI(unittest.TestCase):
    def test_full_pipeline(self):
        t = SelfTuner()
        t.state.step = 20  # 触发调参
        self.assertTrue(t.should_tune())
        f = t.current_fitness(0.5, 0.8)
        self.assertGreater(f, 0)

    def test_meta_vector(self):
        t = SelfTuner()
        mv = t.state.meta
        self.assertIn("certainty", mv.__dict__)
        self.assertIn("effectiveness", mv.__dict__)
        self.assertIn("novelty", mv.__dict__)


class TestValence(unittest.TestCase):
    def test_node_valence(self):
        n = MemoryNode(content="快乐回忆", valence=0.8)
        d = n.to_dict()
        self.assertEqual(d["valence"], 0.8)
        n2 = MemoryNode.from_dict(d)
        self.assertEqual(n2.valence, 0.8)


if __name__ == "__main__":
    unittest.main()