from agents.base import Agent
from llm.router import LLMRouter


class CoderAgent(Agent):
    name = "coder"

    def process(
        self,
        task: str,
        context: dict[str, object] | None = None,
        skill_name: str | None = None,
        skill_params: dict[str, object] | None = None,
    ) -> str:
        return LLMRouter.generate(
            task=task,
            context=context if context is not None else {},
            skill_name=skill_name,
            skill_params=skill_params,
        )
