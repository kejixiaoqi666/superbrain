"""超脑 SuperBrain —— 情感认知内核 + 可靠记忆层的自主 Agent 框架。"""

from .core.agent import SuperBrainAgent, AgentConfig
from .facade import SuperBrain
from .core.llm import LLMProvider, LLMResponse, from_env
from .core.cognition.needs import NeedType, NeedDriveSystem, Need
from .core.cognition.emotion import EmotionGradient, EmotionalState, Expression
from .core.cognition.self_tune import SelfTuner, TuningState
from .core.cognition.neurochem import NeuroChemistry, NeuroChemState
from .core.cognition.metacognition import Metacognition, Reflection
from .core.memory.store import MemoryStore
from .core.memory.node import MemoryNode
from .core.memory.embeddings import HashingEmbedder, embedder_identity
from .core.memory.heat import is_important, retention, due_for_review
from .core.memory.distill import Distiller, Experience, Skill, WikiEntry
from .core.memory.dream import DreamEngine
from .core.memory.concept import ConceptExtractor, ConceptGraph
from .core.memory import dedupe
from .core.memory.working import WorkingMemory, WorkingMemoryItem
from .core.memory.eventlog import EventLog, Event
from .core.memory.time_sense import fuzzy_time, temporal_context, age_in_words
from .core.memory.retrieval import adaptive_search, query_entropy
from .core.memory.expression_guide import analyze_memory_scale, expression_guide
from .core.memory.consolidation import Consolidator
from .core.memory.playbook import ContextPlaybook, PlaybookEntry
from .core.memory.reconsolidation import reconsolidate, ReconsolidationResult
from .core.memory.frontier import EngramMaturation, multi_cue_search
from .core.memory.temporal import detect_conflicts, commit_version
from .core.memory.adaptive import utility, schedule_forgetting, test_time_update
from .core.memory.hierarchical import HierarchicalCondenser
from .core.memory.episodic import EpisodicIndex
from .core.memory.reflective import ReflectiveMemory
from .core.memory.recurrence import RecurrenceGate
from .core.attention import AttentionEngine, attention_block, AttentionFocus
from .core.memory.pisa import SchemaEngine, Schema
from .core.gwt import GlobalWorkspace, Module, Bcast
from .core.tools import Tool, ToolRegistry, PermissionPolicy
from .core.goals import Goal, Task, GoalManager, GoalStatus
from .core.planner import LLMPlanner
from .core.scheduler import Scheduler, ScheduledJob
from .core.autonomous import AutonomousThoughtEngine, AutonomousThought, ThoughtType
from .core.humanize import HumanizeEngine
from .core.meme_tool import search_meme, register_meme_tool
from .core.expression_library import all_categories, all_elements, categories_for, elements_for, pick
from .core.personality.seed import Seed, SeedBank
from .core.personality.values import ValueSystem, CorePrinciple, Preference
from .core.personality.relationship import Relationship, RelationshipGraph
from .core.personality.self_model import SelfModel
from .core.personality.identity import Identity
from .core.personality.dimensions import PersonalityDimensions, Trait
from .core.autonomous_goals import AutonomousGoalEngine, AutonomousGoal, GoalHorizon
from .core.user_profile import UserProfileGraph, UserProfile
from .core.learning import LearningExtractor

__version__ = "2.0.0"

__all__ = [
    "SuperBrainAgent", "AgentConfig", "SuperBrain",
    "LLMProvider", "LLMResponse", "from_env",
    "NeedType", "NeedDriveSystem", "Need",
    "EmotionGradient", "EmotionalState", "Expression",
    "NeuroChemistry", "NeuroChemState",
    "Metacognition", "Reflection",
    "SelfTuner", "TuningState",
    "MemoryStore", "MemoryNode",
    "HashingEmbedder", "embedder_identity",
    "is_important", "retention", "due_for_review",
    "Distiller", "Experience", "Skill", "WikiEntry",
    "DreamEngine",
    "ConceptExtractor", "ConceptGraph", "dedupe",
    "WorkingMemory", "WorkingMemoryItem",
    "EventLog", "Event",
    "fuzzy_time", "temporal_context", "age_in_words",
    "adaptive_search", "query_entropy",
    "analyze_memory_scale", "expression_guide",
    "Consolidator", "ContextPlaybook", "PlaybookEntry",
    "reconsolidate", "ReconsolidationResult",
    "EngramMaturation", "multi_cue_search",
    "detect_conflicts", "commit_version",
    "utility", "schedule_forgetting", "test_time_update",
    "HierarchicalCondenser", "EpisodicIndex", "ReflectiveMemory",
    "SchemaEngine", "Schema", "RecurrenceGate",
    "AttentionEngine", "attention_block", "AttentionFocus",
    "GlobalWorkspace", "Module", "Bcast",
    "Tool", "ToolRegistry", "PermissionPolicy",
    "Goal", "Task", "GoalManager", "GoalStatus",
    "LLMPlanner",
    "Scheduler", "ScheduledJob",
    "AutonomousThoughtEngine", "AutonomousThought", "ThoughtType",
    "HumanizeEngine",
    "search_meme", "register_meme_tool",
    "all_categories", "all_elements", "categories_for", "elements_for", "pick",
    "Seed", "SeedBank",
    "ValueSystem", "CorePrinciple", "Preference",
    "Relationship", "RelationshipGraph",
    "SelfModel",
    "Identity",
    "PersonalityDimensions", "Trait",
    "AutonomousGoalEngine", "AutonomousGoal", "GoalHorizon",
    "UserProfileGraph", "UserProfile",
    "LearningExtractor",
    "__version__",
]
