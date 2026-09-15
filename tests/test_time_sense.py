"""超脑 时间体感测试。"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.time_sense import fuzzy_time, temporal_context, age_in_words


class TestTimeSense(unittest.TestCase):
    def test_recent(self):
        now = time.time()
        self.assertEqual(fuzzy_time(now - 10), "刚才")

    def test_hours_ago(self):
        now = time.time()
        self.assertEqual(fuzzy_time(now - 7200), "2小时前")

    def test_days_ago(self):
        now = time.time()
        self.assertEqual(fuzzy_time(now - 2 * 86400), "2天前")

    def test_years_ago(self):
        now = time.time()
        self.assertEqual(fuzzy_time(now - 3 * 365 * 86400), "3年前")

    def test_none(self):
        self.assertEqual(fuzzy_time(None), "未知时间")

    def test_temporal_context(self):
        self.assertEqual(temporal_context(None), "")

    def test_age(self):
        now = time.time()
        self.assertEqual(age_in_words(now), "刚开始")
