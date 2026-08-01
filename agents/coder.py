from agents.base import Agent

from core.execution_plan import ExecutionPlan

from llm.router import LLMRouter


class CoderAgent(Agent):

    name = "coder"

    role = "Generador e Implementador de Código"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        context["agent_role"] = {
            "name": self.name,
            "responsibility": ("Implementar soluciones técnicas " "siguiendo el ExecutionPlan."),
            "priorities": [
                "Código limpio",
                "Buenas prácticas",
                "Testing",
                "Seguridad",
                "Legibilidad",
                "Compatibilidad con arquitectura existente",
            ],
        }

        return LLMRouter.generate(
            plan=plan,
            context=context,
        )
