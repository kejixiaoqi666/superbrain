"""超脑 注意力/显著性机制测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain.core.attention import AttentionEngine, attention_block


class TestAttention(unittest.TestCase):
    def test_focus_dominant_dimension(self):
        """需求驱动强时焦点应为 need。"""
        a = AttentionEngine()
        f = a.focus(valence=0.1, arousal=0.3, dominant_need="competence",
                    need_drive=0.9, memory_hits=0, input_text="我要做很难的任务")
        self.assertEqual(f.dominant, "need")
        self.assertIn("需求", f.description)

    def test_emotion_focus(self):
        """情绪显著(valence强偏离)时焦点应为 emotion。"""
        a = AttentionEngine()
        f = a.focus(valence=0.95, arousal=0.9, dominant_need="competence",
                    need_drive=0.1, memory_hits=0, input_text="我太高兴了")
        self.assertEqual(f.dominant, "emotion")

    def test_novelty_first_time(self):
        """首次输入新颖性高，二次降低。"""
        a = AttentionEngine()
        f1 = a.focus(0, 0, "competence", 0.1, 0, "全新内容xyz123")
        f2 = a.focus(0, 0, "competence", 0.1, 0, "全新内容xyz123")
        # 新颖性权重二次显著下降（见过）
        self.assertEqual(f1.weights["novelty"], 0.20)  # 首次 = 权重×1.0
        self.assertLess(f2.weights["novelty"], f1.weights["novelty"])  # 二次下降

    def test_block_format(self):
        f = AttentionEngine().focus(0, 0, "competence", 0.8, 0, "任务")
        b = attention_block(f)
        self.assertIn("[注意力]", b)


if __name__ == "__main__":
    unittest.main()