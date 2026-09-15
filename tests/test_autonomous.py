import unittest
from types import SimpleNamespace
from superbrain.core.autonomous import AutonomousThoughtEngine, AutonomousThought, ThoughtType

class TestAutonomous(unittest.TestCase):
    def rels(self, **kw):
        return SimpleNamespace(all=lambda: [SimpleNamespace(**kw)])
    def needs(self, typ, drive):
        return SimpleNamespace(get_dominant_need=lambda: (typ, drive))
    def test_rules_and_cooldown(self):
        now=1_000_000
        r=self.rels(person_id='p',name='小明',familiarity=.8,trust=.8,updated_at=now-700000,notes=[])
        e=AutonomousThoughtEngine(); out=e.generate(self.needs('CERTAINTY',.5),None,r,now)
        self.assertEqual({x.type for x in out},{ThoughtType.MISS,ThoughtType.CURIOUS})
        self.assertEqual(e.generate(self.needs('CERTAINTY',0),None,r,now),[])
    def test_care(self):
        now=1_000_000
        r=self.rels(person_id='p',name='小明',familiarity=.2,trust=.5,updated_at=now,notes=[{'content':'最近很难过','source':'聊天','time':now-10,'confidence':1}])
        self.assertEqual(AutonomousThoughtEngine().generate(self.needs('ENERGY',0),None,r,now)[0].type,ThoughtType.CARE)
    def test_emotion_drive(self):
        """情绪低落（valence<-0.4）→ 触发倾诉（SHARE），emotion 参数真正参与。"""
        now = 1_000_000
        r = self.rels(person_id='p', name='小明', familiarity=.2, updated_at=now, notes=[])
        emo = SimpleNamespace(state=SimpleNamespace(valence=-0.8))
        out = AutonomousThoughtEngine().generate(self.needs('ENERGY', 0), emo, r, now)
        self.assertIn(ThoughtType.SHARE, {x.type for x in out})

    def test_none_queue_persistence(self):
        e=AutonomousThoughtEngine(); self.assertEqual(e.generate(self.needs('ENERGY',.1),None,SimpleNamespace(all=lambda:[]),0),[])
        e.enqueue(AutonomousThought(type='x',content='y',urgency=.2,reason='r',person_id='',created_at=1)); self.assertEqual(e.count,1); self.assertEqual(len(e.drain()),1); self.assertEqual(e.count,0)
        self.assertEqual(AutonomousThoughtEngine.from_dict(e.to_dict()).count,0)

    def test_enqueue_type_guard(self):
        """enqueue 只接受 AutonomousThought，脏对象被忽略（防 asdict 崩）。"""
        e = AutonomousThoughtEngine()
        e.enqueue("bad")            # 非 dataclass 忽略
        e.enqueue({"type": "x"})    # dict 忽略
        self.assertEqual(e.count, 0)
        e.enqueue(AutonomousThought("miss", "x", .5, "r", created_at=1))
        self.assertEqual(e.count, 1)

    def test_share_drive(self):
        """主导需求 relatedness 高 → 触发分享（SHARE）。"""
        now = 1_000_000
        r = self.rels(person_id='p', name='小明', familiarity=.3, updated_at=now, notes=[])
        out = AutonomousThoughtEngine().generate(self.needs('RELATEDNESS', .5), None, r, now)
        self.assertIn(ThoughtType.SHARE, {x.type for x in out})

    def test_pending_and_dirty_restore(self):
        """pending 快照 + from_dict 脏数据防御（坏项跳过、非数值 trigger 过滤）。"""
        e = AutonomousThoughtEngine()
        e.enqueue(AutonomousThought("miss", "x", .5, "r", created_at=1))
        self.assertEqual(len(e.pending), 1)
        e2 = AutonomousThoughtEngine.from_dict({
            "queue": ["bad", {"type": "miss", "content": "y"}],
            "last_trigger": {"p:miss": "notnum", "p:care": 5},
        })
        self.assertEqual(e2.count, 1)           # 非 dict 项被跳过
        self.assertEqual(e2.quiet_hours, 3600)  # 缺失用默认
        self.assertEqual(e2._last_trigger, {"p:care": 5})  # 非数值被过滤

    def test_dirty_notes_defensive(self):
        """脏 note（非dict/time非数值/content非str/source非str）不崩、不误触发。"""
        now = 1_000_000
        r = self.rels(person_id='p', name='小明', familiarity=.5, updated_at=now,
                      notes=[None, "bad", {"time": "notnum", "content": 123, "source": 5}])
        out = AutonomousThoughtEngine().generate(self.needs('ENERGY', 0), None, r, now)
        self.assertEqual(out, [])
