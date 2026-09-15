"""超脑 自动学习测试（LLM 抽取种子/关系/事实）。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.learning import LearningExtractor
from superbrain.core.llm import LLMProvider, LLMResponse


class FakeLLM(LLMProvider):
    def __init__(self):
        pass

    def chat(self, messages, **kw):
        return LLMResponse(content=(
            '{"facts":["用户是开发者"],'
            '"seeds":[{"content":"遇到不确定时先完整表达","trigger":"不确定","bias":"耐心说明","valence":0.6}],'
            '"relationships":[{"person":"creator","note":"喜欢简洁直接"}]}'
        ), finish_reason="stop")


class TestLearningExtractor(unittest.TestCase):
    def test_parse(self):
        raw = '```json\n{"facts":["a"],"seeds":[],"relationships":[]}\n```'
        d = LearningExtractor._parse(raw)
        self.assertEqual(d["facts"], ["a"])

    def test_extract_fake(self):
        ex = LearningExtractor(FakeLLM())
        d = ex.extract("你好", "你好，我是超脑")
        self.assertEqual(d["facts"], ["用户是开发者"])
        self.assertEqual(len(d["seeds"]), 1)
        self.assertEqual(d["relationships"][0]["person"], "creator")


if __name__ == "__main__":
    unittest.main()
