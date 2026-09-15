"""超脑 调度器测试。"""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.scheduler import Scheduler


class TestScheduler(unittest.TestCase):
    def test_due_interval(self):
        s = Scheduler()
        hits = []
        s.add("t", 0.3, lambda: hits.append(1))
        s.start()
        time.sleep(0.8)  # 超过间隔，应触发至少1次
        s.stop()
        self.assertGreaterEqual(len(hits), 1)

    def test_add_remove(self):
        s = Scheduler()
        s.add("t", 10, lambda: None)
        self.assertEqual(len(s.list()), 1)
        s.remove("t")
        self.assertEqual(len(s.list()), 0)

    def test_remove_join_list_concurrent_safe(self):
        """remove/join/list 与并发增删交错不崩。"""
        s = Scheduler()
        s.add("a", 10, lambda: None)
        s.add("b", 20, lambda: None)
        self.assertEqual(len(s.list()), 2)
        s.remove("a")
        self.assertEqual(len(s.list()), 1)
        s.join(0.05)   # 未启动线程时安全
        s.add("c", 5, lambda: None)
        s.start()
        s.remove("b")  # 调度线程运行时并发 remove
        c = len(s.list())
        self.assertGreaterEqual(c, 1)
        s.stop()
        s.join(0.5)    # 停后干净 join
        self.assertEqual(s.list()[0]["name"], "c")


if __name__ == "__main__":
    unittest.main()
