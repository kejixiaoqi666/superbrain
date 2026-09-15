"""超脑 SuperBrain —— MCP server（对接层）。

把超脑核心能力封装成 MCP 工具，供 Codex / Hermes 等 MCP 客户端接入：
- 对话、记忆读写、内在状态、自主关系定位、底层表达元素库、
  自主思考、人性化表达、表情包搜索。

启动：
    python -m superbrain.server_mcp          # stdio 传输（供 Codex/Hermes 本地接入）
    fastmcp run superbrain/server_mcp.py:mcp # 开发调试（--transport http 可起 HTTP）

环境变量：
    SUPERBRAIN_DB   记忆库路径（默认 ~/.superbrain/brain.db）
    SUPERBRAIN_LLM_BASE / _KEY / _MODEL   LLM 配置（缺省用默认）

这是超脑的「对接适配层」，依赖 fastmcp；核心库本身保持零依赖。
"""

from __future__ import annotations

import json
from typing import Optional

from fastmcp import FastMCP

from superbrain import SuperBrain
from superbrain.core.llm import LLMResponse

mcp = FastMCP("superbrain")

_brain: Optional[SuperBrain] = None


class _StubLLM:
    """无超脑 LLM 通道时的降级：核心大脑能力（记忆/状态/关系/表达库/自主思考/表情包）仍可用，
    对话返回空供外层 agent 用自己的 LLM 组织回复。"""

    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="", finish_reason="stop")


def _get_brain() -> SuperBrain:
    """懒装配共享的超脑实例（整个 MCP 进程共用一个大脑 = 一个 db）。

    有 LLM 通道时 from_env 装配（对话可用）；无 LLM 时用 stub 装配，
    保证记忆/状态/关系/表达库等核心能力始终可用。
    """
    global _brain
    if _brain is None:
        try:
            _brain = SuperBrain.from_env()
        except Exception:
            _brain = SuperBrain.from_llm(_StubLLM())
    return _brain


def _dumps(obj) -> str:
    """JSON 序列化（中文不转义）。"""
    return json.dumps(obj, ensure_ascii=False)


@mcp.tool()
def brain_chat(message: str, person_id: str = "") -> str:
    """与超脑对话。person_id 传入时，超脑随相处自主演化对该人的关系。

    返回超脑的回复文本。
    """
    return _get_brain().chat(message, person_id=person_id or None)


@mcp.tool()
def memory_remember(content: str) -> str:
    """让超脑记住一条信息。返回记忆 node id（facade.remember 已返回 str，JSON 兼容）。"""
    return _get_brain().remember(content)


@mcp.tool()
def memory_recall(query: str, k: int = 5) -> str:
    """检索超脑的记忆，返回相关条目列表（content/score/why）。"""
    return _dumps(_get_brain().recall(query, k=k))


@mcp.tool()
def get_state() -> str:
    """查看超脑内在状态：需求/情绪/自主关系定位/自主消息积压/人性化可爱度。"""
    return _dumps(_get_brain().state())


@mcp.tool()
def orientations() -> str:
    """查看超脑对每个人的自主关系定位（相处中自主形成，非绑定标签）。"""
    return _dumps(_get_brain().orientations())


@mcp.tool()
def expression_elements(orientation: str = "") -> str:
    """查看超脑在某关系定位下可用的底层表达元素（框架范围，非锁定）。

    orientation 为空返回全部分类元素；传 lover/friend/close 等返回该定位可选范围。
    """
    return _dumps(_get_brain().expression_elements(orientation or None))


@mcp.tool()
def generate_thoughts() -> str:
    """让超脑基于内在状态产生自主想法（想念/关心/好奇/倾诉等），返回想法列表（纯产生，不入队）。"""
    return _dumps([_thought_dict(t) for t in _get_brain().generate_thoughts()])


@mcp.tool()
def drain_thoughts() -> str:
    """取出超脑待发的自主消息队列（供上层灌进对话）。"""
    return _dumps([_thought_dict(t) for t in _get_brain().drain_thoughts()])


@mcp.tool()
def humanize(text: str, person_id: str = "") -> str:
    """给文本做人性化表达包装（按情绪 + 对某人的亲密度/昵称）。"""
    return _get_brain().humanize(text, person_id=person_id or None)


@mcp.tool()
def search_meme(query: str, limit: int = 5) -> str:
    """搜索表情包，返回图片直链列表（[{url,title,source}]）。"""
    return _dumps(_get_brain().search_meme(query, limit=limit))


@mcp.tool()
def personality_profile() -> str:
    """查看超脑的人格维度画像（可度量的人格维度框架，长出来的，非预设）。"""
    return _dumps(_get_brain().personality())


@mcp.tool()
def set_personality(dimension: str, value: float, note: str = "") -> str:
    """显式设定某人格维度（如用户反馈「你应该更外向」）。返回是否成功。"""
    return _dumps(_get_brain().set_personality(dimension, value, note=note) or False)


@mcp.tool()
def superbrain_tick() -> str:
    """核心一次推进（供上层 agent cron 定时调用）。

    聚合一轮内化推进：需求/情绪/神经化学代谢 + 自主想法生成 + 自主目标生成 +
    人格自省 + 用户画像升格。返回 {thoughts, new_goals, reflected, absorbed} 产出 dict。
    纯产生、不自动发送——上层 agent 据返回决定是否打扰用户。
    超脑是核心库非智能体，自身不做定时/无人值守；由接入的 agent 决定何时调。
    """
    return _dumps(_get_brain().tick())


@mcp.tool()
def personality_mode() -> str:
    """查看超脑当前进化模式：autonomous(自主演化) 或 guided(用户主导)。"""
    return _dumps(_get_brain().personality_mode())


@mcp.tool()
def set_personality_mode(mode: str) -> str:
    """设定超脑进化模式开关：autonomous(自主演化,默认) 或 guided(用户主导,自动通道全停,只听用户)。"""
    return _dumps(_get_brain().set_personality_mode(mode))


@mcp.tool()
def apply_style(style: str) -> str:
    """一句话风格设定（任意自然语言，如可爱/冷静/高冷/傲娇/干练...不锁定）。

    预置风格→映射为大五维度显式设定(explicit)并切 guided；自定义风格→不强套维度、
    仅记录 custom_style 并切 guided（完全听用户）。返回被设定的维度名列表。
    """
    return _dumps(_get_brain().apply_style(style))


@mcp.tool()
def available_styles() -> str:
    """常见风格便捷映射清单（仅作示例，不锁定——任意自然语言风格都可设）。"""
    return _dumps(_get_brain().available_styles())


@mcp.tool()
def style_text() -> str:
    """当前表达风格文本（custom_style，供上层注入 prompt/humanize；空串=未设定）。"""
    return _dumps(_get_brain().style_text())


@mcp.tool()
def generate_goals() -> str:
    """让超脑基于内在状态（需求/情绪/关系/人格维度）涌现中长期自主目标。"""
    return _dumps([_goal_dict(g) for g in _get_brain().generate_goals()])


@mcp.tool()
def autonomous_goals() -> str:
    """查看超脑当前的自主目标清单（active/completed/abandoned）。"""
    return _dumps(_get_brain().autonomous_goals())


@mcp.tool()
def user_profile(person_id: str) -> str:
    """查看对某个人被动积累的用户画像（沟通风格/情绪基调/话题/偏好）。"""
    return _dumps(_get_brain().user_profile(person_id))


def _thought_dict(t) -> dict:
    """自主想法 → 可序列化 dict。"""
    return {
        "type": getattr(t, "type", ""),
        "content": getattr(t, "content", ""),
        "urgency": getattr(t, "urgency", 0.0),
        "reason": getattr(t, "reason", ""),
        "person_id": getattr(t, "person_id", ""),
        "created_at": getattr(t, "created_at", 0.0),
    }


def _goal_dict(g) -> dict:
    """自主目标 → 可序列化 dict。"""
    return {
        "id": getattr(g, "id", ""),
        "content": getattr(g, "content", ""),
        "horizon": getattr(g, "horizon", ""),
        "driven_by": getattr(g, "driven_by", ""),
        "urgency": getattr(g, "urgency", 0.0),
        "reason": getattr(g, "reason", ""),
        "status": getattr(g, "status", ""),
    }


if __name__ == "__main__":
    mcp.run()
