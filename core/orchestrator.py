from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from llm.router import LLMRouter


class Orchestrator:

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()

    def process(self, task: str):
        skill_name, params = LLMRouter.detect_skill(task)

        context_payload = self.context_builder.build(task)
        memory_context = self.memory.get_context()

        if isinstance(memory_context, dict):
            context_payload = {**memory_context, **context_payload}
        else:
            context_payload = {
                "memory": memory_context,
                **context_payload,
            }

        response = LLMRouter.generate(
            task=task,
            context=context_payload,
            skill_name=skill_name,
            skill_params=params
        )

        self.memory.add(task, response)

        return response