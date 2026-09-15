import unittest
from types import SimpleNamespace
from unittest.mock import patch
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


class _P:
    """人格维度 stub：get(name) -> 带 value 的对象。"""
    def __init__(self, d): self._d = d
    def get(self, name):
        v = self._d.get(name)
        return SimpleNamespace(value=v) if v is not None else None


class TestHumanizePersonality(unittest.TestCase):
    """v1.22.1 人格维度/用户画像驱动人性化表达。"""

    def test_agreeableness_gentle(self):
        """高宜人性 → 亲昵门槛降低（熟悉度 0.5 也加轻亲昵）。"""
        p = _P({"agreeableness": 0.9})
        s = HumanizeEngine(0).humanize("好", e(), .5, personality=p)
        self.assertIn("~", s)

    def test_agreeableness_neutral_no_gentle(self):
        p = _P({"agreeableness": 0.4})
        s = HumanizeEngine(0).humanize("好", e(), .5, personality=p)
        self.assertNotIn("~", s)

    def test_neuroticism_emotional(self):
        """高神经质 → 情绪低落阈值放宽，-0.3 即流露『呜呜』。"""
        p = _P({"neuroticism": 0.9})
        self.assertIn("呜呜", HumanizeEngine(0).humanize("累", e(-.3), personality=p))

    def test_neuroticism_normal_threshold(self):
        """默认神经质 → 阈值 -0.4，-0.3 不触发。"""
        p = _P({"neuroticism": 0.3})
        self.assertNotIn("呜呜", HumanizeEngine(0).humanize("累", e(-.3), personality=p))

    def test_user_profile_care(self):
        """用户画像情绪基调低落 → 追加关心。"""
        up = SimpleNamespace(mood_mean=-0.8)
        s = HumanizeEngine(0).humanize("好", e(), user_profile=up)
        self.assertIn("你要好好的", s)

    def test_extraversion_lively(self):
        """高外向性 → 卖萌概率上调（同随机数下更容易出词缀）。"""
        eng = HumanizeEngine(0.4)
        with patch("superbrain.core.humanize.random.random", return_value=0.5):
            affix = eng._choose_affix(e(0, .5), .5, extraversion=0.9)
        self.assertIn(affix, ("喵", "啦", "嗷", "~"))
        with patch("superbrain.core.humanize.random.random", return_value=0.5):
            affix = eng._choose_affix(e(0, .5), .5, extraversion=0.3)
        self.assertEqual(affix, "")

    def test_dirty_personality_defensive(self):
        """脏人格输入（None/无 get）不崩，回退中性默认。"""
        for bad in (None, SimpleNamespace(), {"extraversion": "x"}):
            s = HumanizeEngine(0).humanize("好", e(), personality=bad)
            self.assertIsInstance(s, str)
