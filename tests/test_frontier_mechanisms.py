import tempfile, time, unittest
from superbrain.core.memory.store import MemoryStore
from superbrain.core.memory.node import MemoryNode
from superbrain.core.memory.frontier import EngramMaturation, multi_cue_search

class TestFrontierMechanisms(unittest.TestCase):
    def setUp(self):
        self.path=tempfile.mktemp(suffix='.db'); self.s=MemoryStore(self.path)
    def tearDown(self): self.s.close()
    def test_maturation_sigmoid_and_restart(self):
        n=self.s.add(MemoryNode(content='stable fact', embedding=[1,0], created_at=time.time()-168*3600))
        m=EngramMaturation(self.s); m.register(n.node_id, n.created_at)
        self.assertAlmostEqual(m.activation(n), .5, delta=.01)
        self.assertFalse(m.is_explicit(n, n.created_at+24*3600))
        self.s.close(); self.s=MemoryStore(self.path)
        self.assertEqual(self.s.get_meta('engram:'+n.node_id), str(n.created_at))
    def test_multi_cue_context_and_tags(self):
        a=self.s.add(MemoryNode(content='deploy retry policy', tags=['ops'], embedding=[1,0]))
        b=self.s.add(MemoryNode(content='write poetry', tags=['creative'], embedding=[.9,.1]))
        hits=multi_cue_search(self.s,[1,0],'deploy',k=2,context='deploy ops incident',tags=['ops'])
        self.assertEqual(hits[0][0].node_id,a.node_id)
        self.assertIn('context',hits[0][2]); self.assertIn('tag',hits[0][2])
        # retrieval touch is persisted, not an in-memory-only mutation
        self.assertGreaterEqual(self.s.get(a.node_id).access_count,1)

if __name__=='__main__': unittest.main()
