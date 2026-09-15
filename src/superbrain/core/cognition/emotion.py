"""认知层：情绪梯度系统（内部状态 ≠ 对外表达）。

情绪 = 需求满足率的微分信号，不是标签，是连续梯度场。

关键设计：区分「内部真实状态」和「对外表达」——
同一个"我没事"可能是平静的没事、强撑的没事、或不想让对方担心。
内部估计 ≠ 对外说法，且每个状态带来源、置信度和衰减时间。
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EmotionalState:
    valence: float = 0.0       # 愉悦度 -1..1
    arousal: float = 0.5       # 唤醒度 0..1
    dominance: float = 0.5     # 掌控感 0..1
    confidence: float = 0.5    # 自信 0..1
    # 扩展维度
    certainty: float = 0.5     # 确定感 0..1
    safety: float = 0.5        # 安全感 0..1
    fatigue: float = 0.0       # 疲惫度 0..1
    attachment: float = 0.5    # 依恋 0..1

    def to_dict(self) -> dict:
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "confidence": round(self.confidence, 3),
            "certainty": round(self.certainty, 3),
            "safety": round(self.safety, 3),
            "fatigue": round(self.fatigue, 3),
            "attachment": round(self.attachment, 3),
        }


@dataclass
class Expression:
    """对外表达（可能与内部状态不一致）。"""
    text: str = ""             # 对外说法（如"我没事"）
    intensity: float = 0.5     # 实际对外表达强度 0..1
    deviation: float = 0.0     # 与内部状态的偏差（>0 表示压抑/强撑）
    reason: str = ""           # 为何这样表达（如"不想让对方担心"）


class EmotionGradient:
    """情绪从需求满足率的变化率自然涌现，用指数平滑保持连续感。"""

    def __init__(self, alpha: float = 1.0, beta: float = 0.5, gamma: float = 0.8,
                 smoothing: float = 0.3) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.smoothing = smoothing
        self.state = EmotionalState()
        self.expression = Expression()
        self._need_history: deque = deque(maxlen=100)   # 有上限，防无限增长
        self._reward_history: deque = deque(maxlen=200)  # 有上限，防无限增长

    def update(self, satisfactions: Dict[str, float],
               task_success: Optional[float] = None,
               novelty: Optional[float] = None) -> EmotionalState:
        self._need_history.append(satisfactions)
        avg = statistics.mean(satisfactions.values())
        v_target = max(-1.0, min(1.0, 2.0 * avg - 1.0))
        self.state.valence = self._smooth(self.state.valence, v_target)

        if len(self._need_history) >= 2:
            prev = self._need_history[-2]
            curr = self._need_history[-1]
            deltas = [curr[k] - prev.get(k, 0.5) for k in curr]
            drive = min(1.0, abs(statistics.mean(deltas)) * 3)
        else:
            drive = 0.3
        self.state.arousal = self._smooth(self.state.arousal, 0.3 + 0.7 * drive)

        if task_success is not None:
            self.state.dominance = self._smooth(self.state.dominance, 0.2 + 0.8 * task_success)
        if novelty is not None:
            self.state.confidence = self._smooth(self.state.confidence, max(0.0, min(1.0, 1.0 - novelty)))
        return self.state

    def set_expression(self, text: str, intensity: Optional[float] = None,
                       reason: str = "") -> None:
        """设置对外表达，自动计算与内部状态的偏差（识别"强撑"）。"""
        self.expression.text = text
        self.expression.intensity = intensity if intensity is not None else \
            (self.state.valence + 1.0) / 2.0
        # 偏差 = 对外表达的积极程度 vs 内部真实 valence
        expressed_positivity = self.expression.intensity
        internal_positivity = (self.state.valence + 1.0) / 2.0
        self.expression.deviation = abs(expressed_positivity - internal_positivity)
        self.expression.reason = reason

    @property
    def masking(self) -> bool:
        """是否在压抑情绪（对外积极但内部消极）。"""
        return (self.expression.deviation > 0.3 and
                self.state.valence < 0 and
                self.expression.intensity > 0.5)

    def compute_intrinsic_reward(self) -> float:
        vd = 0.0
        if len(self._need_history) >= 2:
            vd = statistics.mean(list(self._need_history[-1].values())) \
                 - statistics.mean(list(self._need_history[-2].values()))
        r = max(-1.0, min(1.0, self.alpha * vd + self.beta * (1.0 - self.state.confidence)
                          + self.gamma * self.state.arousal))
        self._reward_history.append(r)
        return r

    @property
    def mean_reward(self, window: int = 20) -> float:
        r = list(self._reward_history)[-window:] if self._reward_history else [0.0]
        return statistics.mean(r)

    def _smooth(self, old: float, new: float) -> float:
        return old * self.smoothing + new * (1.0 - self.smoothing)

    def reset(self) -> None:
        self.state = EmotionalState()
        self.expression = Expression()
        self._need_history.clear()
        self._reward_history.clear()
