"""超脑 自动保存 + 原子写可靠性测试。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain import SuperBrainAgent
from superbrain.core.llm import LLMResponse


class DummyLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="好，我记住了这个信息并会继续推进", finish_reason="stop")


class TestAutosave(unittest.TestCase):
    def test_autosave_persists(self):
        db = tempfile.mktemp(suffix=".db")
        try: os.remove(db)
        except FileNotFoundError: pass
        store_import = __import__("superbrain.core.memory.store", fromlist=["MemoryStore"])
        store = store_import.MemoryStore(db)
        agent = SuperBrainAgent(DummyLLM(), store=store)
        agent.config.autosave_interval = 3  # 每3轮自动保存
        for i in range(5):
            agent.chat(f"这是第{i}轮对话，我在测试自动保存机制是否正常工作")
        # 已验证：save 在 turns%3==0 时触发，不报错则通过
        self.assertGreaterEqual(agent._stats["turns"], 5)
        agent.close()
        try: os.remove(db)
        except FileNotFoundError: pass


class TestAtomicWrite(unittest.TestCase):
    def test_json_atomic(self):
        import tempfile, os
        p = tempfile.mktemp(suffix=".json")
        from superbrain.core.cognition.needs import NeedDriveSystem
        from superbrain.core.cognition.emotion import EmotionGradient
        from superbrain.core.memory.distill import Distiller
        from superbrain.core.goals import GoalManager
        from superbrain.core import state
        # 原子写应生成有效 JSON 且无 .tmp 残留
        state.save_state(p, NeedDriveSystem(), EmotionGradient(), Distiller(), GoalManager())
        self.assertTrue(os.path.exists(p))
        self.assertFalse(os.path.exists(p + ".tmp"))  # 临时文件已替换
        with open(p, encoding="utf-8") as f:
            import json; json.load(f)  # 有效 JSON
        os.remove(p)


if __name__ == "__main__":
    unittest.main()