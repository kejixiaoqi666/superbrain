"""超脑 上下文清洗（防污染）测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.context_cleaner import clean_tool_output, clean_history_message, is_noise


class TestContextCleaner(unittest.TestCase):
    def test_clean_json(self):
        """JSON 工具输出 → 摘要，不整段污染。"""
        long_val = "很长" * 100  # 200 字符，超 50 截断阈值
        out = clean_tool_output('{"a": 1, "b": "%s", "c": [1,2,3]}' % long_val)
        self.assertIn("{", out)
        self.assertIn("...", out)  # 长值被截断标记
        self.assertLess(len(out), 120)  # 摘要长度受控

    def test_clean_traceback(self):
        """堆栈 → 只留最后错误行。"""
        tb = "Traceback (most recent call last):\n  File x.py line 1\n  File y.py line 2\nValueError: 出错了"
        out = clean_tool_output(tb)
        self.assertIn("出错了", out)
        self.assertNotIn("x.py", out)  # 堆栈中间行被剥离

    def test_clean_empty(self):
        """空输出 → 丢弃。"""
        self.assertEqual(clean_tool_output("   "), "")
        self.assertEqual(clean_tool_output(""), "")

    def test_noise_detection(self):
        """噪声检测。"""
        self.assertTrue(is_noise("  "))
        self.assertTrue(is_noise("。。"))
        self.assertTrue(is_noise("aaaaaaa"))
        self.assertFalse(is_noise("这是一个有意义的句子"))

    def test_history_clean_tool(self):
        """历史 tool 消息清洗。"""
        out = clean_history_message('{"result": "ok", "data": {"x": 1}}', "tool")
        self.assertIn("{", out)  # 摘要而非整段

    def test_history_long_truncate(self):
        """历史长消息截断。"""
        long = "很" * 1000
        out = clean_history_message(long, "user")
        self.assertLess(len(out), 400)


if __name__ == "__main__":
    unittest.main()
