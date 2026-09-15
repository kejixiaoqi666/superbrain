import tempfile, unittest, os
from superbrain import MemoryStore, MemoryNode, RecurrenceGate
class TestRecurrence(unittest.TestCase):
 def test_gate_and_persist(self):
  p=tempfile.mktemp(); s=MemoryStore(p); g=RecurrenceGate(s)
  a=MemoryNode(content='用户喜欢蓝色', embedding=[1.0]); self.assertFalse(g.consolidate(a).node_id)
  b=g.consolidate(MemoryNode(content='用户喜欢蓝色', embedding=[1.0])); self.assertTrue(b.node_id); self.assertIsNotNone(s.get(b.node_id)); s.conn.close(); os.unlink(p)
 def test_no_false_trigger_on_unrelated(self):
  """语义无关的记忆不应误触发（Jaccard 相似度相对阈值，非绝对 n-gram 数）。"""
  s=MemoryStore(tempfile.mktemp()); g=RecurrenceGate(s)
  g.consolidate(MemoryNode(content='用户喜欢蓝色汽车'))
  # 语义完全无关的长句，不应因绝对 n-gram 重叠而误触发
  r=g.consolidate(MemoryNode(content='服务器部署在云端需要配置防火墙规则'))
  self.assertFalse(r.node_id)  # 未触发，node_id 为空
 if __name__=='__main__': unittest.main()
