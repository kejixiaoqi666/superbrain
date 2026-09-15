"""超脑 LLM 通道层测试：HTTP 响应解析、from_env、token 估算、工具调用。"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain.core.llm import LLMProvider, LLMResponse, ToolCall, estimate_tokens, from_env


class _FakeResp:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._payload


class TestToolCall(unittest.TestCase):
    def test_args_dict(self):
        self.assertEqual(ToolCall("1", "f", '{"x": 1}').args_dict(), {"x": 1})
        self.assertEqual(ToolCall("1", "f", "").args_dict(), {})
        self.assertEqual(ToolCall("1", "f", "bad json").args_dict(), {})  # 脏 JSON 容错


class TestEstimateTokens(unittest.TestCase):
    def test_chinese(self):
        self.assertEqual(estimate_tokens("你好世界"), 4)
        self.assertEqual(estimate_tokens(""), 0)

    def test_english(self):
        self.assertEqual(estimate_tokens("hello world"), 2)  # 11字符/4≈2

    def test_mixed(self):
        self.assertEqual(estimate_tokens("你好 hello"), 3)  # 2 + 7/4 → int(3.75)=3


class TestFromEnv(unittest.TestCase):
    def tearDown(self):
        for k in ("SUPERBRAIN_LLM_BASE", "SUPERBRAIN_LLM_KEY",
                  "SUPERBRAIN_LLM_MODEL", "DPDNS_DEEPSEEK_API_KEY"):
            os.environ.pop(k, None)

    def test_missing_key_raises(self):
        with self.assertRaises(RuntimeError):
            from_env()

    def test_from_env_constructs(self):
        os.environ["SUPERBRAIN_LLM_BASE"] = "https://x/v1"
        os.environ["SUPERBRAIN_LLM_KEY"] = "sk-test"
        os.environ["SUPERBRAIN_LLM_MODEL"] = "m1"
        p = from_env()
        self.assertEqual(p.base_url, "https://x/v1")
        self.assertEqual(p.model, "m1")

    def test_fallback_env_key(self):
        os.environ["DPDNS_DEEPSEEK_API_KEY"] = "sk-fallback"
        p = from_env()
        self.assertEqual(p.api_key, "sk-fallback")


class TestLLMProviderChat(unittest.TestCase):
    def _provider(self):
        return LLMProvider("https://api.test/v1", "sk-k", "model-x")

    @mock.patch("superbrain.core.llm.urllib.request.urlopen")
    def test_chat_parses_response(self, mock_urlopen):
        mock_urlopen.return_value = _FakeResp({
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": "你好", "reasoning_content": "思考"}
            }]
        })
        p = self._provider()
        resp = p.chat([{"role": "user", "content": "hi"}])
        self.assertIsInstance(resp, LLMResponse)
        self.assertEqual(resp.content, "你好")
        self.assertEqual(resp.reasoning, "思考")
        self.assertEqual(resp.finish_reason, "stop")
        self.assertEqual(resp.tool_calls, [])

    @mock.patch("superbrain.core.llm.urllib.request.urlopen")
    def test_chat_parses_tool_calls(self, mock_urlopen):
        mock_urlopen.return_value = _FakeResp({
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "c1", "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "x"}'},
                    }]
                }
            }]
        })
        p = self._provider()
        resp = p.chat([{"role": "user", "content": "查一下"}], tools=[{"name": "search"}])
        self.assertEqual(resp.finish_reason, "tool_calls")
        self.assertEqual(len(resp.tool_calls), 1)
        self.assertEqual(resp.tool_calls[0].name, "search")
        self.assertEqual(resp.tool_calls[0].args_dict(), {"q": "x"})

    @mock.patch("superbrain.core.llm.urllib.request.urlopen")
    def test_chat_request_body_includes_tools(self, mock_urlopen):
        mock_urlopen.return_value = _FakeResp({"choices": [{"message": {"content": "ok"}}]})
        req = {}

        def fake_urlopen(r, timeout=None):
            req["body"] = json.loads(r.data.decode())
            req["url"] = r.full_url
            return _FakeResp({"choices": [{"message": {"content": "ok"}}]})

        mock_urlopen.side_effect = fake_urlopen
        p = self._provider()
        p.chat([{"role": "user", "content": "hi"}], tools=[{"name": "t"}], max_tokens=512)
        self.assertIn("tools", req["body"])
        self.assertEqual(req["body"]["max_tokens"], 512)
        self.assertIn("/chat/completions", req["url"])


if __name__ == "__main__":
    unittest.main()