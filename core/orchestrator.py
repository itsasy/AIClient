from llm.router import LLMRouter
from core.context_builder import ContextBuilder
from core.memory import ConversationMemory

class Orchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()
    
    def process(self, task: str):
        context = self.memory.get_context() + self.context_builder.build(task)
        return LLMRouter.generate(context)
