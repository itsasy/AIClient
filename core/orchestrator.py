import logging

from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class Orchestrator:

    def process(self, task):

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