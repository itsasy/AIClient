from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan

from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):

    name = "planner"

    role = "Planificador de ejecución"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = dict(context or {})

        logger.info(
            "Generando plan para '%s'",
            plan.original_task,
        )

        plan.execution_mode = "multi_step"

        planning_context = self._build_planning_context(
            context,
        )

        response = LLMRouter.generate(
            plan=plan,
            context=planning_context,
        )

        self._load_steps(
            plan,
            response,
        )

        if not plan.steps:

            logger.warning("Planner no generó pasos.")

        return self._format_plan(
            plan,
        )

    # ==========================================================
    # Context
    # ==========================================================

    def _build_planning_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        planning = {}

        allowed = [
            "project",
            "documents",
            "obsidian",
            "gentleman",
            "standards",
            "spec",
        ]

        for key in allowed:

            value = context.get(
                key,
            )

            if value:

                planning[key] = value

        if "engram" in context:

            planning["engram"] = context["engram"]

        return planning

    # ==========================================================
    # Steps parser
    # ==========================================================

    def _load_steps(
        self,
        plan: ExecutionPlan,
        response: str,
    ) -> None:

        try:

            plan.steps.clear()

            data = self._extract_json(
                response,
            )

            if not isinstance(
                data,
                list,
            ):

                logger.warning("Planner no devolvió lista de pasos.")

                return

            for item in data:

                if not isinstance(
                    item,
                    dict,
                ):

                    continue

                description = item.get(
                    "description",
                )

                if not description:

                    continue

                plan.add_step(
                    description=description,
                    skill=item.get(
                        "skill",
                    ),
                    tool=item.get(
                        "tool",
                    ),
                    provider=item.get(
                        "provider",
                    ),
                    params=item.get(
                        "params",
                        {},
                    ),
                )

        except Exception:

            logger.exception("Error cargando pasos del planner.")

    def _extract_json(
        self,
        response: str,
    ) -> list | dict | None:

        start = response.find(
            "[",
        )

        end = response.rfind(
            "]",
        )

        if start == -1 or end == -1:

            return None

        payload = response[start : end + 1]

        return json.loads(
            payload,
        )

    # ==========================================================
    # Validation
    # ==========================================================

    def validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> list[str]:

        errors = []

        if not plan.original_task:

            errors.append("Planner requiere una tarea.")

        return errors

    # ==========================================================
    # Output
    # ==========================================================

    def _format_plan(
        self,
        plan: ExecutionPlan,
    ) -> str:

        output = [
            "# Plan de ejecución",
            "",
            f"Objetivo: {plan.objective or plan.original_task}",
            "",
            "Pasos:",
        ]

        for index, step in enumerate(
            plan.steps,
            start=1,
        ):

            suffix = ""

            if step.skill:

                suffix += f" [{step.skill}]"

            if step.tool:

                suffix += f" ({step.tool})"

            output.append(f"{index}. {step.description}{suffix}")

        return "\n".join(
            output,
        )
