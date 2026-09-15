import json
import unittest
from unittest.mock import patch

from superbrain.core.meme_tool import search_meme, register_meme_tool
from superbrain.core.meme_tool import _CACHE

# 模拟 memegen.link /templates 的真实返回结构（数组）
TEMPLATES = [
    {"id": "t1", "name": "Grumpy Cat", "keywords": ["cat"], "blank": "https://x/t1.jpg",
     "example": {"url": "https://x/t1_ex.jpg"}, "source": "knowyourmeme"},
    {"id": "t2", "name": "Dog", "keywords": [], "blank": "https://x/t2.jpg"},
    {"id": "t3", "name": "Ancient Aliens Guy", "keywords": ["history channel"], "blank": "https://x/t3.jpg"},
]


class TestMemeTool(unittest.TestCase):
    def setUp(self):
        # 清模块级模板缓存：避免跨测试泄漏污染在线结果
        _CACHE["templates"] = []
        _CACHE["ts"] = 0.0

    def _mock_online(self, payload=None):
        data = json.dumps(payload if payload is not None else TEMPLATES).encode()
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = data
        return patch("superbrain.core.meme_tool.urllib.request.urlopen", return_value=response)

    def test_online_match_and_limit(self):
        """在线模板库按 name/keywords 匹配 + limit 截断。"""
        with self._mock_online():
            result = search_meme("cat", limit=1)
        self.assertEqual(result, [{"url": "https://x/t1.jpg", "title": "Grumpy Cat",
                                   "source": "memegen"}])

    def test_online_no_match_fallback(self):
        """在线不匹配 → 降级本地索引；本地也无 → 空。"""
        with self._mock_online():
            self.assertTrue(search_meme("开心"))              # 在线无命中 → 本地 twemoji
            self.assertEqual(search_meme("不存在词xyz"), [])   # 在线+本地都无

    def test_network_failure_degrades(self):
        """网络失败 → 优雅降级本地索引，不抛错。"""
        with patch("superbrain.core.meme_tool.urllib.request.urlopen", side_effect=TimeoutError()):
            self.assertTrue(search_meme("猫"))
            self.assertEqual(search_meme("不存在的词"), [])

    def test_invalid_input(self):
        self.assertEqual(search_meme(""), [])
        self.assertEqual(search_meme("xx", limit=0), [])
        self.assertEqual(search_meme(123), [])

    def test_local_index_dedup(self):
        """本地索引多关键词命中去重保序。"""
        with patch("superbrain.core.meme_tool.urllib.request.urlopen", side_effect=OSError()):
            r = search_meme("开心哈哈", limit=10)
        urls = [e["url"] for e in r]
        self.assertEqual(len(urls), len(set(urls)))  # 不重复

    def test_register_function_calling_signature(self):
        """handler 必须能被 ToolRegistry.call(**kwargs) 调用（曾因 handler(arguments) 崩）。"""
        from superbrain.core.tools import ToolRegistry
        reg = ToolRegistry()
        register_meme_tool(reg)
        out = reg.call("search_meme", query="开心", limit=3)
        parsed = json.loads(out)
        self.assertIsInstance(parsed, list)
        self.assertTrue(parsed)

    def test_dict_response_compat(self):
        """在线 API 返回 dict{results:...} 也兼容解析。"""
        with self._mock_online({"results": [{"id": "c1", "name": "Cat", "keywords": ["猫"],
                                             "blank": "https://x/c.jpg"}]}):
            r = search_meme("cat", limit=1)
        self.assertEqual(r[0]["url"], "https://x/c.jpg")


if __name__ == "__main__":
    unittest.main()