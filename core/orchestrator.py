import logging

from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()

    def process(self, task: str):
        skill_name, params = LLMRouter.detect_skill(task)
        logger.info("Procesando tarea con skill=%s: %s", skill_name, task)

        full_context = self.memory.get_context()
        project_context = self.context_builder.build(task)
        if project_context and project_context not in full_context:
            full_context += project_context

        response = LLMRouter.generate(
            task=task,
            context=full_context,
            skill_name=skill_name,
            skill_params=params,
        )

        self.memory.add(task, response)
        return response