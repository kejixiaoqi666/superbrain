"""超脑 对话浓缩测试（v1.22.1）：旧对话提炼为要点常青记忆，细节降级遗忘。"""
import os
import sys
import time
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from superbrain import SuperBrain
from superbrain.core.llm import LLMResponse
from superbrain.core.memory.store import MemoryStore


class SummaryLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="用户偏好蓝莓口味，需要 docker 部署，计划扩展租机。",
                           finish_reason="stop")


class EmptyLLM:
    def chat(self, messages, tools=None, **kw):
        return LLMResponse(content="", finish_reason="stop")


def _brain(llm):
    db = tempfile.mktemp(suffix=".db")
    try:
        os.remove(db)
    except FileNotFoundError:
        pass
    b = SuperBrain.from_llm(llm(), store=MemoryStore(db))
    b._agent.config.enable_learning = False
    b._agent.config.autosave = False
    b._agent.config.enable_tuning = False
    return b


def _make_old_session(brain, n=6):
    now = time.time()
    ids = []
    for i in range(n):
        nid = brain.remember(f"用户偏好 docker 部署 {i}", scope="session")
        brain._agent.store.conn.execute(
            "UPDATE nodes SET created_at=? WHERE node_id=?", (now - 5 * 86400, nid))
        ids.append(nid)
    brain._agent.store._commit_if_autonomous()
    return ids


class TestCondense(unittest.TestCase):
    def test_condense_produces_essence(self):
        """LLM 路径：旧 session 记忆浓缩成 user 常青要点，原始细节降级 archival。"""
        b = _brain(SummaryLLM)
        _make_old_session(b)
        r = b._agent._condense_session_memories(window_hours=72, min_batch=5)
        self.assertEqual(r["condensed"], 1)
        self.assertEqual(r["forgotten"], 6)
        user_mem = [n for n in b._agent.store.all_nodes()
                    if n.scope == "user" and "condensed" in (n.tags or [])]
        self.assertEqual(len(user_mem), 1)
        self.assertIn("蓝莓", user_mem[0].content)
        # 原始 session 全部降级（遗忘细节，物理不删）
        self.assertTrue(all(n.tier == "archival"
                            for n in b._agent.store.by_scope("session")))
        b.close()

    def test_heuristic_fallback_no_llm(self):
        """无 LLM（返回空）时退化为启发式浓缩，仍能产出要点。"""
        b = _brain(EmptyLLM)
        _make_old_session(b)
        r = b._agent._condense_session_memories(window_hours=72, min_batch=5)
        self.assertEqual(r["condensed"], 1)
        self.assertEqual(r["forgotten"], 6)
        b.close()

    def test_below_min_batch_skips(self):
        """不足 min_batch 条旧对话时不浓缩（避免碎浓缩）。"""
        b = _brain(SummaryLLM)
        _make_old_session(b, n=3)
        r = b._agent._condense_session_memories(window_hours=72, min_batch=5)
        self.assertEqual(r["condensed"], 0)
        b.close()

    def test_db_size_limit(self):
        """记忆库物理上限：db_size / over_size_limit 可查，上限可配置。"""
        b = _brain(SummaryLLM)
        self.assertGreaterEqual(b._agent.store.db_size(), 0)
        self.assertFalse(b._agent.store.over_size_limit())  # 空库未超限
        b._agent.store.max_db_bytes = 1   # 设为极小，模拟超限
        self.assertTrue(b._agent.store.over_size_limit())
        b.close()


if __name__ == "__main__":
    unittest.main()