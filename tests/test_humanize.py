import unittest
from superbrain.core.humanize import HumanizeEngine
from superbrain.core.cognition.emotion import EmotionalState

def e(v=0,a=.5): return EmotionalState(valence=v, arousal=a)

class TestHumanize(unittest.TestCase):
 def test_cute_extremes(self):
  self.assertNotIn("喵", HumanizeEngine(0).humanize("好",e()))
  self.assertIn(HumanizeEngine(1)._choose_affix(e(0,.5),.5), ("喵","啦","嗷","~"))
 def test_nickname_and_intimacy(self):
  s=HumanizeEngine(0).humanize("吃饭了吗",e(),.8,"小七")
  self.assertIn("小七",s); self.assertIn("贴贴",s)
 def test_emotions(self):
  self.assertIn("嘿嘿",HumanizeEngine(0).humanize("太好了",e(.8)))
  self.assertIn("呜呜",HumanizeEngine(0).humanize("我累了",e(-.8)))
 def test_thresholds_and_neutral(self):
  self.assertNotIn("贴贴",HumanizeEngine(0).humanize("好",e(),.69))
  self.assertIn("啦",HumanizeEngine(0).humanize("好",e(),.5))
 def test_no_network(self):
  self.assertIsInstance(HumanizeEngine().humanize("x",e()),str)
 def test_low_valence_intimate_comfort(self):
  """低落 + 高亲密度 → 求安慰，且不叠贴贴。"""
  s = HumanizeEngine(0).humanize("我累了", e(-.8), .8, "小七")
  self.assertIn("呜呜", s); self.assertIn("关心我一下", s); self.assertNotIn("贴贴", s)
 def test_high_arousal(self):
  """高唤醒 → 加『！！真的』。"""
  self.assertIn("！！真的", HumanizeEngine(0).humanize("中奖了", e(0, .9)))
 def test_no_nickname_intimate(self):
  """高亲密度无昵称 → 用哎哎哎。"""
  self.assertIn("哎哎哎", HumanizeEngine(0).humanize("好", e(), .8))
 def test_to_from_dict(self):
  """可爱度持久化往返 + 默认。"""
  self.assertEqual(HumanizeEngine.from_dict(HumanizeEngine(0.9).to_dict()).cute_probability, 0.9)
  self.assertEqual(HumanizeEngine.from_dict({}).cute_probability, 0.5)
 def test_affix_appended(self):
  """cute=1 时卖萌词缀被追加到结尾（高唤醒分支后）。"""
  s = HumanizeEngine(1).humanize("哈哈哈", e(0, .3))
  self.assertIn("哈哈哈", s)
  self.assertTrue(s.endswith(("喵", "啦", "嗷", "~")))
