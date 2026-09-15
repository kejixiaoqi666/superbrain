"""基于情绪与亲密度的规则化人性化表达。"""
import random
from .cognition.emotion import EmotionalState

class HumanizeEngine:
    """不联网、不调用模型的轻量表达包装器。"""
    def __init__(self, cute_probability=0.5):
        self.cute_probability = max(0.0, min(1.0, cute_probability))

    def _choose_affix(self, emotion_state, familiarity):
        """按情绪调制卖萌概率，返回确定的词缀或空串。cute_probability=0 时彻底不卖萌。"""
        if self.cute_probability <= 0:
            return ""
        # 熟悉度加成：越亲近越容易自然卖萌
        probability = (self.cute_probability
                       + max(0.0, emotion_state.arousal - .5) * .4
                       + max(0.0, familiarity - .5) * .3)
        if random.random() >= min(1.0, probability):
            return ""
        return ("喵", "啦", "嗷", "~")[int(emotion_state.arousal * 10) % 4]

    def humanize(self, text, emotion_state: EmotionalState, familiarity=0.5, nickname=""):
        if not isinstance(familiarity, (int, float)):
            familiarity = 0.5  # 脏熟悉度防御，避免 None>=.7 崩
        if text is None:
            text = ""
        result = str(text)
        low = emotion_state.valence < -.4   # 情绪低落
        if familiarity >= .7:
            prefix = (nickname + "~") if nickname else "哎哎哎"
            result = prefix + result
            if not low:
                result += "贴贴"  # 低落时不叠"贴贴"，避免"贴贴+呜呜"语义矛盾
        if emotion_state.valence > .4:
            result += "，嘿嘿"
        elif low:
            result += "，呜呜"
            if familiarity >= .6:
                result += "，你能不能关心我一下"
        elif not result.endswith(("啦", "呀", "哦")):
            result += "啦"
        if emotion_state.arousal > .7:
            result += "！！真的"
        affix = self._choose_affix(emotion_state, familiarity)
        if affix and not result.endswith(affix):
            result += affix
        return result

    def to_dict(self) -> dict:
        return {"cute_probability": self.cute_probability}

    @classmethod
    def from_dict(cls, d: dict) -> "HumanizeEngine":
        return cls(cute_probability=d.get("cute_probability", 0.5))
