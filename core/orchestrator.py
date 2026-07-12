from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from llm.router import LLMRouter


class Orchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()

    def process(self, task: str) -> str:
        skill_name, skill_params = LLMRouter.detect_skill(task)

        context = self.context_builder.build(task)
        context.update(self.memory.get_context())

        response = LLMRouter.generate(
            task=task,
            context=context,
            skill_name=skill_name,
            skill_params=skill_params,
        )

        self.memory.add(task, response)

        return response