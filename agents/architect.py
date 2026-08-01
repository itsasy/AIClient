from agents.base import Agent

from core.execution_plan import ExecutionPlan

from llm.router import LLMRouter


class ArchitectAgent(Agent):

    name = "architect"

    role = "Arquitecto de Software"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        context["agent_role"] = {
            "name": self.name,
            "responsibility": (
                "Analizar requisitos, diseñar soluciones " "y definir decisiones arquitectónicas."
            ),
            "priorities": [
                "Clean Architecture",
                "SOLID",
                "DDD",
                "Escalabilidad",
                "Mantenibilidad",
                "Seguridad",
            ],
        }

        return LLMRouter.generate(
            plan=plan,
            context=context,
        )
