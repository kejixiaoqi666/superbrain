import unittest
import tempfile
from superbrain.core.memory.playbook import ContextPlaybook
from superbrain.core.memory.reconsolidation import reconsolidate
from superbrain.core.memory.node import MemoryNode
from superbrain.core.memory.store import MemoryStore


class TestFrontier(unittest.TestCase):
    def test_delta_grow_refine(self):
        p = ContextPlaybook()
        p.curate([p.delta('retry', 'use bounded retry', True)])
        p.curate([p.delta('retry', 'log the cause', False)])
        self.assertIn('log the cause', p.render())
        self.assertEqual(p.entries['retry'].uses, 2)

    def test_reconsolidation_gate(self):
        """预测误差门控：小误差不动，大误差才更新并写回 store。"""
        db = tempfile.mktemp(suffix='.db')
        s = MemoryStore(db)
        n = MemoryNode(content='x', confidence=0.8, retention_strength=2.0,
                       embedding=[1.0])
        s.add(n)
        # 小误差（0.8 vs 0.7 = 0.1 < 0.25）：不动
        r = reconsolidate(s, n.node_id, 0.7)
        self.assertFalse(r.updated)
        self.assertEqual(s.get(n.node_id).confidence, 0.8)
        # 大误差（0.8 vs 0.1 = 0.7 > 0.25）：更新，retention 下降（记忆被动摇）
        r = reconsolidate(s, n.node_id, 0.1)
        self.assertTrue(r.updated)
        node2 = s.get(n.node_id)
        self.assertLess(node2.confidence, 0.8)           # 置信度向观察值移动
        self.assertLess(node2.retention_strength, 2.0)   # retention 下降（方向正确）
        s.close()


if __name__ == '__main__':
    unittest.main()
