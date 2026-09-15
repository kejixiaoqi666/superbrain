import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from superbrain import MemoryStore, MemoryNode, schedule_forgetting, test_time_update
class TestAdaptive(unittest.TestCase):
 def test_feedback_persists_and_surprise_decreases(self):
  with tempfile.TemporaryDirectory() as d:
   s=MemoryStore(os.path.join(d,'m.db')); n=s.add(MemoryNode(content='x',embedding=[1]))
   before=s.get(n.node_id).retention_strength; test_time_update(s,n.node_id,False,1.0)
   self.assertLess(s.get(n.node_id).retention_strength,before)
 def test_schedule_demotes_low_utility(self):
  with tempfile.TemporaryDirectory() as d:
   s=MemoryStore(os.path.join(d,'m.db')); n=s.add(MemoryNode(content='x',confidence=0.0,tier='recall'))
   self.assertIn(n.node_id,schedule_forgetting(s,0,floor=1.0)); self.assertEqual(s.get(n.node_id).tier,'archival')
 def test_success_converges_not_unbounded(self):
  with tempfile.TemporaryDirectory() as d:
   s=MemoryStore(os.path.join(d,'m.db')); n=s.add(MemoryNode(content='x',embedding=[1]))
   # 反复 success 后 retention 应收敛到温和目标(3.0)，不无限累加到上限10
   for _ in range(100): test_time_update(s,n.node_id,True,0.0)
   self.assertLessEqual(s.get(n.node_id).retention_strength, 3.5)
if __name__=='__main__': unittest.main()
