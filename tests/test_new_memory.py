import unittest, tempfile, os
from superbrain import MemoryStore, MemoryNode, HierarchicalCondenser, EpisodicIndex
class TestNewMemory(unittest.TestCase):
 def setUp(self): self.f=tempfile.NamedTemporaryFile(delete=False); self.s=MemoryStore(self.f.name); self.f.close()
 def tearDown(self): self.s.close(); os.unlink(self.f.name)
 def n(self,i,v,kind='fact'): return MemoryNode(node_id=i,content=v,embedding=[1.,0.] if i!='b' else [0.,1.],kind=kind)
 def test_hierarchy_persistent(self):
  h=HierarchicalCondenser(self.s,.5); h.insert(self.n('a','alpha')); h.insert(self.n('b','beta')); self.assertEqual(len(h.descendants()),2); self.assertTrue(any(k=='hierarchy' for *_,k,_ in self.s.all_edges()))
 def test_episode_time_and_edges(self):
  e=EpisodicIndex(self.s); g=self.n('g','event', 'gist'); f=self.n('f','fact'); g.created_at=10; e.add_episode(g,[f]); self.assertEqual([x.node_id for x in e.between(9,11)],['g']); self.assertEqual(self.s.all_edges()[0][3],'episode-fact')
 def test_root_is_real_node(self):
  h=HierarchicalCondenser(self.s,.5); h.insert(self.n('a','alpha'))
  root_id=h._root()
  root=self.s.get(root_id)
  self.assertIsNotNone(root)              # 根是真实节点
  self.assertEqual(root.kind,'hierarchy_root')
  self.assertEqual(root.content,'__hierarchy_root__')
 def test_gist_index_persists_across_restart(self):
  e=EpisodicIndex(self.s); g=self.n('g','event','gist'); g.created_at=5; e.add_episode(g,[])
  self.s.close()
  s2=MemoryStore(self.f.name)             # 重启
  e2=EpisodicIndex(s2)
  self.assertEqual([x.node_id for x in e2.between(0,10)],['g'])  # 索引持久化
  s2.close()
if __name__=='__main__': unittest.main()
