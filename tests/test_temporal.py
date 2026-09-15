import tempfile, time, unittest
from superbrain import MemoryStore, MemoryNode, commit_version


class TestTemporal(unittest.TestCase):
    def test_version_persists(self):
        """冲突版本提交后，旧节点失效并持久化（重启不丢）。"""
        p = tempfile.mktemp()
        s = MemoryStore(p)
        t = time.time()
        # 同实体"截止日期"，值从 4月 变为 5月（字面有重叠，n-gram 可识别）
        a = s.add(MemoryNode(content="项目截止日期是4月", created_at=t - 1))
        commit_version(s, MemoryNode(content="项目截止日期是5月", created_at=t), t)
        # 旧节点应已失效
        self.assertFalse(s.get(a.node_id).is_valid(t + 1))
        s.close()
        # 重启后仍失效（持久化）
        s = MemoryStore(p)
        self.assertFalse(s.get(a.node_id).is_valid(t + 1))
        s.close()


if __name__ == '__main__':
    unittest.main()
