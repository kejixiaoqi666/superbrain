import tempfile, unittest
from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode
from superbrain.core.memory.consolidation import Consolidator

class ConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db'); self.tmp.close()
        self.s = MemoryStore(self.tmp.name)
    def tearDown(self): self.s.close()
    def test_opt_in_candidate_sleep_strengthens_without_scanning_others(self):
        a=MemoryNode(content='important', embedding=[1.0], access_count=3, confidence=1)
        b=MemoryNode(content='other', embedding=[1.0], access_count=0, confidence=1)
        self.s.add(a); self.s.add(b)
        out=Consolidator(self.s).sleep([a], max_items=1)
        self.assertEqual(out['considered'],1)
        self.assertEqual(self.s.get(a.node_id).tier,'core')
        self.assertEqual(self.s.get(b.node_id).tier,'recall')
    def test_active_forgetting_is_reversible_and_preserves_provenance(self):
        n=MemoryNode(content='stale', embedding=[1.0], created_at=1, last_access=1)
        self.s.add(n)
        out=Consolidator(self.s).sleep([n], forget_below=0.01)
        self.assertEqual(out['forgotten'],[n.node_id])
        self.assertIsNotNone(self.s.get(n.node_id))
        self.assertEqual(self.s.get(n.node_id).tier,'archival')  # 降级不删除

if __name__=='__main__': unittest.main()
