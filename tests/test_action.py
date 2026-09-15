"""超脑 SuperBrain 行动层 + 目标系统测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from superbrain.core.tools import ToolRegistry, Tool, PermissionPolicy, register_builtin_tools
from superbrain.core.goals import GoalManager, GoalStatus
from superbrain.core.cognition.needs import NeedType


class TestTools(unittest.TestCase):
    def test_register_and_call(self):
        reg = ToolRegistry()
        reg.register(Tool(
            name="echo", description="回显", parameters={"type": "object", "properties": {}},
            handler=lambda **kw: "ok",
        ))
        self.assertEqual(reg.call("echo"), "ok")
        self.assertEqual(len(reg.list()), 1)

    def test_builtin_read(self):
        reg = ToolRegistry()
        register_builtin_tools(reg)
        r = reg.call("read_file", path="/etc/hostname")
        self.assertIsInstance(r, str)

    def test_permission(self):
        p = PermissionPolicy()
        self.assertTrue(p.needs_approval("exec", "system", "exec"))
        self.assertTrue(p.needs_approval("write_file", "file", "write"))
        self.assertFalse(p.needs_approval("read_file", "file", "read"))


class TestGoals(unittest.TestCase):
    def test_derive_goal(self):
        gm = GoalManager()
        g = gm.derive_goal(NeedType.COMPETENCE, 0.8)
        self.assertIsNotNone(g)
        self.assertEqual(g.driven_by, "competence")

    def test_weak_drive_no_goal(self):
        gm = GoalManager()
        g = gm.derive_goal(NeedType.ENERGY, 0.1)
        self.assertIsNone(g)

    def test_decompose_and_progress(self):
        gm = GoalManager()
        g = gm.derive_goal(NeedType.CERTAINTY, 0.7)
        gm.decompose(g, ["步骤1", "步骤2", "步骤3"])
        self.assertEqual(len(g.tasks), 3)
        self.assertEqual(g.status, GoalStatus.IN_PROGRESS.value)
        # 依赖顺序：只能先做步骤1
        nxt = gm.next_task(g)
        self.assertEqual(nxt.description, "步骤1")
        gm.complete_task(g, nxt.id)
        self.assertEqual(gm.next_task(g).description, "步骤2")


if __name__ == "__main__":
    unittest.main()
