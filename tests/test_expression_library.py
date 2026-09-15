"""底层表达元素库测试：关系定位决定可用元素范围，超脑自主选用。"""

import unittest

from superbrain.core.expression_library import (
    all_categories, categories_for, elements_for, pick,
)


class TestExpressionLibrary(unittest.TestCase):
    def test_categories_scope_grows_with_relationship(self):
        """关系越深（orientation 越高），可选元素类别越丰富。"""
        self.assertEqual(categories_for("stranger"), [])
        self.assertTrue(set(categories_for("acquaintance")) <= set(categories_for("friend")))
        self.assertTrue(set(categories_for("friend")) <= set(categories_for("lover")))
        self.assertIn("affection", categories_for("lover"))  # 深情只在 lover 级

    def test_elements_for_is_scope_not_force(self):
        """elements_for 返回「可用范围」，非强制内容。"""
        e = elements_for("lover")
        self.assertIn("affection", e)
        self.assertIn("coquetry", e)
        self.assertNotIn("affection", elements_for("friend"))  # friend 级无深情

    def test_pick_autonomous_selection(self):
        """pick 按关系定位自主选用元素；越界不自作主张返回空。"""
        self.assertEqual(pick("lover", "affection", 0), "你来了灯就亮了")
        self.assertEqual(pick("lover", "affection", 3), "你来了灯就亮了")  # index 循环
        self.assertEqual(pick("friend", "affection"), "")   # 关系不到位不可用
        self.assertEqual(pick("stranger", "care"), "")      # 陌生级不可用关心
        self.assertEqual(pick("close", "intimacy", 0), "贴贴")

    def test_all_categories(self):
        """框架清单完整列出底层元素类别。"""
        cats = all_categories()
        for expected in ["endearment", "coquetry", "care", "affection",
                         "intimacy", "joy", "sadness", "casual"]:
            self.assertIn(expected, cats)

    def test_dirty_orientation_defensive(self):
        """脏 orientation/category（list/dict/None 不可 hash）不崩返回空。"""
        self.assertEqual(elements_for([]), {})
        self.assertEqual(elements_for({}), {})
        self.assertEqual(categories_for([]), [])
        self.assertEqual(pick([], "affection"), "")
        self.assertEqual(pick("lover", []), "")
        self.assertEqual(pick(None, None), "")
        self.assertEqual(pick(0, 0), "")


if __name__ == "__main__":
    unittest.main()