import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode
from superbrain.core.memory.reflective import ReflectiveMemory
class TestReflective(unittest.TestCase):
 def test_persist_and_bounded_feedback(self):
  p=tempfile.mktemp(); s=MemoryStore(p); n=s.add(MemoryNode(content='用户喜欢茶'))
  ReflectiveMemory(s).retrospective([n.node_id], success=False)
  s.close(); s=MemoryStore(p); self.assertLess(s.get(n.node_id).retention_strength,1.0)
  s.close(); os.unlink(p)
 def test_prospective_links_real_nodes(self):
  s=MemoryStore(tempfile.mktemp()); a=s.add(MemoryNode(content='甲')); b=s.add(MemoryNode(content='乙'))
  r=ReflectiveMemory(s).prospective([a,b],'偏好'); self.assertEqual(len(s.neighbors(r.node_id)),2)
 def test_retrospective_converges_not_unbounded(self):
  p=tempfile.mktemp(); s=MemoryStore(p); n=s.add(MemoryNode(content='x',retention_strength=10.0))
  r=ReflectiveMemory(s)
  # 反复失败 → retention 收敛到 0.1 下限附近，不涨
  for _ in range(50): r.retrospective([n.node_id], success=False)
  self.assertLess(s.get(n.node_id).retention_strength, 1.0)
  s.close(); os.unlink(p)
if __name__=='__main__': unittest.main()
