import json
import logging

from agents.base import Agent

from core.execution_plan import ExecutionPlan

from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):

    name = "planner"

    role = "Planificador"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        logger.info(
            "Generando plan para '%s'",
            plan.original_task,
        )

        planning_context = self._build_planning_context(context)

        response = LLMRouter.generate(
            plan=plan,
            context=planning_context,
        )

        self._load_steps(
            plan,
            response,
        )

        plan.execution_mode = "multi_step"

        return self._format_plan(plan)

    # ---------------------------------------------------------

    def _build_planning_context(
        self,
        context: dict,
    ) -> dict:

        planning = {}

        if "engram" in context:

            planning["engram_memory"] = context["engram"].get("memory")

            planning["engram_skills"] = context["engram"].get("skills")

        if "gentleman" in context:

            planning["gentleman"] = context["gentleman"]

        if "standards" in context:

            planning["standards"] = context["standards"]

        if "project" in context:

            planning["project"] = context["project"]

        if "documents" in context:

            planning["documents"] = context["documents"]

        if "obsidian" in context:

            planning["obsidian"] = context["obsidian"]

        return planning

    # ---------------------------------------------------------

    def _load_steps(
        self,
        plan: ExecutionPlan,
        response: str,
    ):

        try:

            start = response.find("[")
            end = response.rfind("]") + 1

            if start == -1:

                logger.warning("El planner no devolvió pasos.")

                return

            steps = json.loads(
                response[start:end],
            )

            for step in steps:

                plan.add_step(
                    description=step.get(
                        "description",
                        "Paso sin descripción",
                    ),
                    skill=step.get(
                        "skill",
                    ),
                    params=step.get(
                        "params",
                        {},
                    ),
                )

        except Exception:

            logger.exception("No fue posible cargar los pasos.")

    # ---------------------------------------------------------

    def _format_plan(
        self,
        plan: ExecutionPlan,
    ) -> str:

        output = [
            "# Plan de ejecución",
            "",
            f"Objetivo: {plan.objective}",
            "",
            "Pasos:",
        ]

        for i, step in enumerate(
            plan.steps,
            start=1,
        ):

            skill = f" [{step.skill}]" if step.skill else ""

            output.append(f"{i}. {step.description}{skill}")

        return "\n".join(output)
