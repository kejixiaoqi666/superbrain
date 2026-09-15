"""超脑 服务层测试：HTTP API 端点可调。"""

import json
import os
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain import SuperBrain
from superbrain.server import start
from superbrain.core.llm import LLMResponse


class StubLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="好的", finish_reason="stop")


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        from superbrain.core.memory.store import MemoryStore
        db = tempfile.mktemp(suffix=".db")
        brain = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        brain._agent.config.enable_learning = False
        brain._agent.config.autosave = False
        brain._agent.config.enable_tuning = False
        cls.brain = brain
        cls.server = start(brain=brain, port=8091)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.brain.close()

    def _post(self, path, payload=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:8091{path}",
            data=json.dumps(payload or {}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:8091{path}", timeout=5) as r:
            return json.loads(r.read().decode())

    def test_health(self):
        self.assertEqual(self._get("/health")["status"], "ok")

    def test_tools_list(self):
        tools = self._post("/tools")["tools"]
        self.assertIn("chat", tools)
        self.assertIn("remember", tools)
        self.assertIn("recall", tools)

    def test_chat(self):
        r = self._post("/chat", {"message": "你好"})
        self.assertIn("reply", r)

    def test_remember_recall(self):
        r = self._post("/remember", {"content": "用户喜欢蓝色"})
        self.assertTrue(r["node_id"])
        hits = self._post("/recall", {"query": "用户喜欢"})["hits"]
        self.assertIsInstance(hits, list)


if __name__ == "__main__":
    unittest.main()