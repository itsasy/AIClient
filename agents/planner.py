import json
import logging

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.spec_manager import SpecManager
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):

    name = "planner"

    role = "Planificador SDD"

    def __init__(self):

        self.spec_manager = SpecManager()
        self.provider_manager = ProviderManager()

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        logger.info(
            "Generando plan SDD para: %s",
            plan.original_task,
        )

        generated_steps = self._generate_steps(
            plan,
            context or {},
        )

        if not generated_steps:

            return "❌ No fue posible generar " "pasos de ejecución."

        for step in generated_steps:

            plan.add_step(
                description=step.get(
                    "description",
                    "Paso sin descripción",
                ),
                skill=step.get("skill"),
                params=step.get(
                    "params",
                    {},
                ),
            )

        plan.execution_mode = "multi_step"

        return self._format_plan(plan)

    def _generate_steps(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> list | None:

        provider, fallback_chain = ProviderSelector.select(
            task=plan.original_task,
            skill_name="plan",
        )

        prompt = f"""
Eres un arquitecto de software experto en SDD.

Genera un plan ejecutable basado en la siguiente tarea.

Tarea:
{plan.original_task}


Objetivo:
{plan.objective}


Contexto:
{context}


Devuelve SOLO JSON.

Formato:

[
 {{
   "description": "Crear estructura inicial",
   "skill": "write_file",
   "params": {{
       "path": "archivo.txt",
       "content": "contenido"
   }}
 }}
]


Skills disponibles:

- code
- write_file
- shell
- docker
- analyze
- laravel_project
- full_project

"""

        try:

            response = self.provider_manager.generate(
                prompt,
                provider_name=provider,
                fallback_chain=fallback_chain,
            )

            start = response.find("[")
            end = response.rfind("]") + 1

            if start == -1:
                return None

            return json.loads(response[start:end])

        except Exception:

            logger.exception("Error generando plan")

            return None

    def _format_plan(
        self,
        plan: ExecutionPlan,
    ) -> str:

        output = [
            f"## 📋 Plan generado",
            "",
            f"Objetivo: {plan.objective or plan.original_task}",
            "",
            "Pasos:",
        ]

        for index, step in enumerate(
            plan.steps,
            start=1,
        ):

            output.append(f"{index}. " f"{step.description}" f" [{step.skill}]")

        output.append("", "Estado: listo para ejecución.")

        return "\n".join(output)
