"""超脑 论文落地测试：WikiSkill/MemSkill/TokenPilot/MemGAS。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.memory.distill import Distiller
from superbrain.core.memory.retrieval import query_entropy


class TestWikiSkill(unittest.TestCase):
    def test_wiki_persists_across_rollback(self):
        d = Distiller()
        d.record_wiki("用户说稍等时不应追问", kind="lesson", confidence=0.6)
        d.update_skill("回复", "追问细节")
        d.update_skill("回复", "追问更多细节")
        d.rollback_skill("回复")
        # Wiki 经验不受 Skill 回滚影响
        self.assertEqual(len(d.wiki_patterns()), 1)
        self.assertEqual(d.wiki_patterns()[0].pattern, "用户说稍等时不应追问")

    def test_wiki_reinforce(self):
        d = Distiller()
        d.record_wiki("重复模式", confidence=0.5)
        d.record_wiki("重复模式", confidence=0.5)
        w = d.wiki_patterns()[0]
        self.assertEqual(w.reinforced, 1)  # 第二次强化而非新增

    def test_skill_rollback(self):
        d = Distiller()
        d.update_skill("写代码", "版本1")
        d.update_skill("写代码", "版本2")
        s = d.rollback_skill("写代码")
        self.assertEqual(s.procedure, "版本1")  # 回滚到上一版
        self.assertEqual(s.version, 3)

    def test_designer_evolve(self):
        """MemSkill Designer：从 hard case 演化 skill 集。"""
        d = Distiller()
        d.update_skill("回复", "旧流程")
        d.record_hard_case("回复", "用户生气", "回复太生硬")
        def refine(case):
            if "生气" in case["task"]:
                return ("回复", "先安抚再回应")
            return None
        results = d.design_skills(refine)
        self.assertEqual(len(results), 1)
        self.assertEqual(d._skills["回复"].procedure, "先安抚再回应")
        self.assertEqual(d._skills["回复"].version, 2)  # 演化带版本


class TestTokenPilot(unittest.TestCase):
    def test_artifact_threshold(self):
        # 阈值逻辑在 agent._dispatch_tool，这里测配置存在
        from superbrain import AgentConfig
        c = AgentConfig()
        self.assertGreater(c.artifact_threshold, 0)


class TestMemGAS(unittest.TestCase):
    def test_entropy_high_for_vague(self):
        self.assertGreater(query_entropy("帮我"), query_entropy("帮我查 192.168.1.1 的端口 443"))

    def test_entropy_range(self):
        for q in ["", "帮我", "查一下2024年deepseek-v4的评测分数和API价格"]:
            e = query_entropy(q)
            self.assertGreaterEqual(e, 0.0)
            self.assertLessEqual(e, 1.0)


if __name__ == "__main__":
    unittest.main()
