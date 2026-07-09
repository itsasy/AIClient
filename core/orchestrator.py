from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from llm.router import LLMRouter


class Orchestrator:

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()

    def process(self, task: str):

        skill_name, params = LLMRouter.detect_skill(task)

        context = (
            self.memory.get_context()
            + self.context_builder.build(task)
        )

        response = LLMRouter.generate(
            task=task,
            context=context,
            skill_name=skill_name,
            skill_params=params
        )

        self.memory.add(task, response)

        return response