from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from llm.router import LLMRouter


class Orchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()

    def process(self, task: str):
        context = self.memory.get_context() + self.context_builder.build(task)
        response = LLMRouter.generate(context)
        self.memory.add(task, response)
        return response
