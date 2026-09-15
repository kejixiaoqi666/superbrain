"""超脑 神经化学 + 元认知测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.cognition.neurochem import NeuroChemistry
from superbrain.core.cognition.metacognition import Metacognition


class TestNeuroChemistry(unittest.TestCase):
    def test_release_observe(self):
        nc = NeuroChemistry()
        nc.release(dopamine=0.3, serotonin=0.2)
        self.assertGreater(nc.state.dopamine, 0.5)  # 释放后上升
        self.assertGreater(nc.state.serotonin, 0.5)

    def test_decay_momentum(self):
        nc = NeuroChemistry()
        nc.release(cortisol=0.8)
        co_before = nc.state.cortisol
        nc.tick(dt_hours=5)  # 半衰期后显著下降（残留/滞后）
        self.assertLess(nc.state.cortisol, co_before)

    def test_observe_from_emotion(self):
        nc = NeuroChemistry()
        nc.observe(valence=-0.8, arousal=0.9)  # 消极+高唤醒 → 皮质醇
        self.assertGreater(nc.state.cortisol, 0.5)


class TestMetacognition(unittest.TestCase):
    def test_reflect_high_conf_low_outcome(self):
        m = Metacognition()
        r = m.reflect("决策X", reasoning_quality=0.8, confidence=0.9, outcome=-0.8)
        self.assertGreater(m.cautiousness, 0.5)  # 高估后更谨慎

    def test_trend(self):
        m = Metacognition()
        for i in range(5):
            m.reflect(f"决策{i}", reasoning_quality=0.8, confidence=0.5, outcome=0.5)
        self.assertGreater(m.reasoning_trend(), 0.6)

    def test_assess(self):
        m = Metacognition()
        a = m.assess_pending(confidence=0.2)
        self.assertTrue(a["should_pause"])  # 太不确定该暂停
