"""Offline memory-only example; no network or model API is used."""
from pathlib import Path
from tempfile import TemporaryDirectory
from superbrain import SuperBrain
from superbrain.core.llm import LLMResponse
from superbrain.core.memory.store import MemoryStore

class OfflineLLM:
    def chat(self, messages, tools=None, **kwargs):
        return LLMResponse(content="offline demo")

with TemporaryDirectory() as directory:
    brain = SuperBrain.from_llm(OfflineLLM(), store=MemoryStore(Path(directory) / "brain.db"))
    brain.remember("这个项目使用 Python，回答先给结论再给步骤")
    print(brain.recall("项目使用什么语言"))
    print(brain.state()["memory_nodes"])
    brain.close()
