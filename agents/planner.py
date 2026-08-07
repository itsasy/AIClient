from __future__ import annotations

import json
import logging
import re
from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan


from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):
    """
    Agente encargado de construir ExecutionPlans multi-step.
    """

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

        # Log para depuración (opcional, pero útil)
        logger.info("Respuesta del planner: %s", response[:500])

        self._load_steps(
            plan,
            response,
        )

        if not plan.steps:

            logger.warning(
                "Planner no generó pasos.",
            )

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

        planning: dict[str, Any] = {}

        allowed = (
            "project",
            "documents",
            "obsidian",
            "gentleman",
            "standards",
            "spec",
            "engram",
        )

        for key in allowed:

            value = context.get(
                key,
            )

            if value is not None:

                planning[key] = value

        # ✅ Instrucciones claras para el LLM
        planning["instructions"] = (
            "Genera un plan de ejecución en formato JSON, con una lista de pasos. "
            "Cada paso debe tener los campos: 'description' (string), "
            "'unit_type' (string, puede ser 'agent' o 'skill'), "
            "'unit_name' (string, nombre del agente o skill), "
            "y opcionalmente 'params' (objeto con parámetros). "
            "Devuelve SOLO el JSON, sin texto adicional, sin markdown, sin comillas triples. "
            'Ejemplo: [{"description": "Analizar requisitos", "unit_type": "agent", "unit_name": "architect"}]'
        )

        return planning

    # ==========================================================
    # Steps
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

                logger.warning(
                    "Planner no devolvió una lista de pasos. Datos: %s",
                    data,
                )

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
                    unit_type=item.get(
                        "unit_type",
                    ),
                    unit_name=item.get(
                        "unit_name",
                    ),
                    params=item.get(
                        "params",
                        {},
                    ),
                )

        except Exception:

            logger.exception(
                "Error cargando pasos del planner.",
            )

    def _extract_json(
        self,
        response: str,
    ) -> list | dict | None:
        """
        Extrae JSON de la respuesta del LLM, manejando código markdown y texto adicional.
        """

        # 1. Limpiar posibles bloques de código markdown
        response = re.sub(r"```json\s*", "", response)
        response = re.sub(r"```\s*", "", response)
        response = response.strip()

        # 2. Buscar primero un array [...]
        start = response.find("[")
        end = response.rfind("]")

        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(response[start : end + 1])
            except json.JSONDecodeError:
                pass

        # 3. Si no hay array, buscar un objeto {...}
        start = response.find("{")
        end = response.rfind("}")

        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(response[start : end + 1])
            except json.JSONDecodeError:
                pass

        # 4. Si nada funciona, intentar parsear la respuesta completa
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("No se pudo extraer JSON de la respuesta.")
            return None

    # ==========================================================
    # Validation
    # ==========================================================

    def validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> list[str]:

        errors = []

        if not plan.original_task:

            errors.append(
                "Planner requiere una tarea.",
            )

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

            if step.unit_type:

                suffix += f" [{step.unit_type}]"

            if step.unit_name:

                suffix += f" {step.unit_name}"

            output.append(
                f"{index}. {step.description}{suffix}",
            )

        return "\n".join(
            output,
        )
