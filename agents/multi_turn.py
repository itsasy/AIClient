from agents.base import Agent
from llm.router import LLMRouter


class MultiTurnAgent(Agent):
    name = "multi_turn"
    role = "Agente conversacional con memoria"

    def process(
        self,
        task: str,
        context: dict[str, object] | None = None,
        skill_name: str | None = None,
        skill_params: dict[str, object] | None = None,
    ) -> str:
        history = ""

        if context is not None:
            history = str(context.get("memory", ""))

        prompt = f"""Historial:
{history}

Nueva tarea:
{task}

Mantén coherencia y contexto."""

        return LLMRouter.generate(
            task=prompt,
            context=context if context is not None else {},
            skill_name=skill_name,
            skill_params=skill_params,
        )
