"""超脑 工作记忆 + 事件日志测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.working import WorkingMemory
from superbrain.core.memory.eventlog import EventLog


class TestWorkingMemory(unittest.TestCase):
    def test_capacity_limit(self):
        wm = WorkingMemory(capacity=3)
        for i in range(5):
            wm.add(f"item{i}")
        self.assertEqual(len(wm.items), 3)  # 只留最近3条
        self.assertEqual(wm.recent(1), ["item4"])  # 最新的是 item4

    def test_task_pending(self):
        wm = WorkingMemory()
        wm.set_task("帮用户解决问题")
        wm.add_pending("查资料")
        wm.add_pending("写代码")
        wm.done_pending("查资料")
        s = wm.summary()
        self.assertIn("帮用户解决问题", s)
        self.assertIn("写代码", s)
        self.assertNotIn("查资料", s)  # 已完成移除


class TestEventLog(unittest.TestCase):
    def test_append_only(self):
        log = EventLog()
        log.append("conversation", "hello")
        log.append("learning", "seed created")
        self.assertEqual(len(log), 2)
        self.assertEqual(log.recent(1)[0].kind, "learning")

    def test_roundtrip(self):
        log = EventLog()
        log.append("conversation", "测试事件", provenance="direct_observation")
        d = log.to_dict()
        log2 = EventLog.from_dict(d)
        self.assertEqual(len(log2), 1)
        self.assertEqual(log2._events[0].content, "测试事件")


if __name__ == "__main__":
    unittest.main()