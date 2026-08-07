from __future__ import annotations

import logging

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.execution_result import ExecutionResult

from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillRuntime:
    """
    Runtime encargado de ejecutar Skills.

    Responsabilidades:

    - Resolver Skill desde registry.
    - Ejecutar capacidad.
    - Normalizar resultados.

    No:

    - Decide qué skill usar.
    - Construye planes.
    - Gestiona herramientas externas.
    - Gestiona lifecycle.
    """

    name = "skill_runtime"

    def __init__(
        self,
        registry: SkillRegistry,
    ) -> None:

        self.registry = registry

    # ==================================================
    # Public API
    # ==================================================

    def execute(
        self,
        skill_name: str,
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        params = dict(
            params or {},
        )

        plan = params.pop(
            "plan",
            None,
        )

        step = params.pop(
            "step",
            None,
        )

        context = params.pop(
            "context",
            {},
        )

        if not isinstance(
            plan,
            ExecutionPlan,
        ):

            plan = ExecutionPlan(
                original_task=params.get(
                    "task",
                    "",
                ),
                execution_unit_type="skill",
                execution_unit=skill_name,
            )

        try:

            skill = self.registry.get(
                skill_name,
            )

            if not skill:

                return ExecutionResult.fail(
                    error=f"Skill no encontrada: {skill_name}",
                    executor=self.name,
                )

            warnings = []

            if isinstance(
                step,
                ExecutionStep,
            ):

                warnings = skill.validate_step(
                    step,
                )

            else:

                step = ExecutionStep(
                    description=skill.name,
                    unit_type="skill",
                    unit_name=skill.name,
                    params=params,
                )

            result = skill.execute(
                plan,
                step,
                {
                    **context,
                    **params,
                },
            )

            metadata = {
                "runtime": self.name,
                "skill": skill.name,
            }

            if warnings:

                metadata["warnings"] = warnings

            return ExecutionResult.success(
                result=result,
                executor=skill.name,
                metadata=metadata,
            )

        except Exception as exc:

            logger.exception(
                "Error ejecutando skill=%s",
                skill_name,
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=self.name,
            )

    # ==================================================
    # Information
    # ==================================================

    def available_skills(
        self,
    ) -> list[str]:

        return self.registry.list()
