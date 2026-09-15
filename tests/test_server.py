"""超脑 HTTP 服务层测试（v1.22.1）：起真实服务 + 请求各端点。"""
import json
import os
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain import SuperBrain
from superbrain.core.llm import LLMResponse
from superbrain.core.memory.store import MemoryStore
from superbrain.server import start
import tempfile


class StubLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="好的", finish_reason="stop")


class TestHTTPServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = tempfile.mktemp(suffix=".db")
        try:
            os.remove(db)
        except FileNotFoundError:
            pass
        brain = SuperBrain.from_llm(StubLLM(), store=MemoryStore(db))
        brain._agent.config.enable_learning = False
        brain._agent.config.autosave = False
        brain._agent.config.enable_tuning = False
        cls._db = db
        srv = start(brain=brain, host="127.0.0.1", port=0)
        cls.srv = srv
        cls.base = f"http://127.0.0.1:{srv.server_address[1]}"
        cls._t = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._t.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        try:
            os.remove(cls._db)
        except FileNotFoundError:
            pass

    def _req(self, path, payload=None, method=None):
        url = self.base + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_health(self):
        code, body = self._req("/health")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "ok")

    def test_state(self):
        code, body = self._req("/state")
        self.assertEqual(code, 200)
        self.assertIn("needs", body)

    def test_chat(self):
        code, body = self._req("/chat", {"message": "你好"})
        self.assertEqual(code, 200)
        self.assertIn("reply", body)

    def test_remember_recall(self):
        code, body = self._req("/remember", {"content": "HTTP 测试记忆"})
        self.assertEqual(code, 200)
        self.assertIn("node_id", body)
        code2, body2 = self._req("/recall", {"query": "HTTP 测试"})
        self.assertEqual(code2, 200)
        self.assertIn("hits", body2)

    def test_tools(self):
        code, body = self._req("/tools", method="POST")
        self.assertEqual(code, 200)
        self.assertIn("tools", body)
        self.assertIn("chat", body["tools"])

    def test_humanize(self):
        code, body = self._req("/humanize", {"text": "好的", "person_id": "u1"})
        self.assertEqual(code, 200)
        self.assertIn("text", body)

    def test_thoughts_and_drain(self):
        code, body = self._req("/thoughts", method="POST")
        self.assertEqual(code, 200)
        self.assertIn("thoughts", body)
        code2, body2 = self._req("/drain_thoughts", method="POST")
        self.assertEqual(code2, 200)
        self.assertIn("thoughts", body2)

    def test_orientations(self):
        code, body = self._req("/orientations", method="POST")
        self.assertEqual(code, 200)

    def test_404(self):
        code, body = self._req("/nonexistent", {})
        self.assertEqual(code, 404)
        self.assertIn("error", body)

    def test_bad_json_ok(self):
        """脏 JSON 请求体 → 当作空 dict，不崩。"""
        code, _ = self._bad("/state")
        self.assertEqual(code, 200)

    def _bad(self, path):
        import urllib.error
        req = urllib.request.Request(self.base + path, data=b"not json",
                                     method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()