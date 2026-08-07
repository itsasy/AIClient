from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Constructor declarativo de ExecutionPlans.
    """

    name = "execution_planner"

    @classmethod
    def create(cls, task: str, intent: dict[str, Any] | None = None) -> ExecutionPlan:
        if not task or not task.strip():
            raise ValueError("ExecutionPlanner requiere una tarea.")

        intent = intent or {}
        plan = ExecutionPlan(original_task=task.strip())

        intent_name = cls._normalize(intent.get("intent", "conversation"))
        domain = cls._normalize(intent.get("domain", "general"))
        complexity = cls._normalize(intent.get("complexity", "normal"))

        plan.intent = intent_name
        plan.intent_category = domain

        plan.metadata.update(
            {
                "planner": cls.name,
                "intent": intent_name,
                "domain": domain,
                "complexity": complexity,
            }
        )

        if complexity in {"high", "complex"}:
            plan.execution_mode = "multi_step"
        else:
            plan.execution_mode = "single"

        planner_method = getattr(cls, f"_plan_{intent_name}", cls._plan_default)
        planner_method(plan, task.strip())

        errors = plan.validate()
        if errors:
            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        plan.mark_planned()
        logger.info("ExecutionPlan creado intent=%s mode=%s", intent_name, plan.execution_mode)

        return plan

    @staticmethod
    def _normalize(value: str | None) -> str:
        if not value:
            return ""
        return value.lower().strip().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _set_execution_unit(
        plan: ExecutionPlan,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        plan.execution_unit_type = ExecutionPlan.normalize_unit_type(unit_type)
        plan.execution_unit = unit_name
        plan.params = params or {}

    @staticmethod
    def _plan_project_creation(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Crear un nuevo proyecto de software"
        plan.execution_mode = "multi_step"

        analyze = plan.add_step(
            description="Analizar requisitos del proyecto",
            unit_type="agent",
            unit_name="architect",
            params={"task": task},
        )
        generate = plan.add_step(
            description="Generar estructura inicial",
            unit_type="agent",
            unit_name="coder",
            params={"task": task},
        )
        generate.depends_on.append(analyze.id)

    @staticmethod
    def _plan_code_generation(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Generar código"
        ExecutionPlanner._set_execution_unit(plan, "agent", "coder", {"task": task})

    @staticmethod
    def _plan_debug(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Analizar y resolver problema técnico"
        plan.execution_mode = "multi_step"
        analyze = plan.add_step(
            description="Analizar problema",
            unit_type="agent",
            unit_name="coder",
            params={"task": task},
        )
        validate = plan.add_step(
            description="Ejecutar validaciones",
            unit_type="skill",
            unit_name="sandbox",
            params={"task": task},
        )
        validate.depends_on.append(analyze.id)

    @staticmethod
    def _plan_refactor(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Refactorizar código existente"
        plan.execution_mode = "multi_step"
        analyze = plan.add_step(
            description="Analizar arquitectura actual",
            unit_type="agent",
            unit_name="architect",
            params={"task": task},
        )
        modify = plan.add_step(
            description="Aplicar cambios",
            unit_type="agent",
            unit_name="coder",
            params={"task": task},
        )
        modify.depends_on.append(analyze.id)

    @staticmethod
    def _plan_documentation(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Crear documentación"
        ExecutionPlanner._set_execution_unit(plan, "agent", "writer", {"task": task})

    @staticmethod
    def _plan_file_creation(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Crear archivo"
        ExecutionPlanner._set_execution_unit(plan, "skill", "write_file", {"task": task})

    @staticmethod
    def _plan_command_execution(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Ejecutar comando"
        ExecutionPlanner._set_execution_unit(plan, "skill", "shell", {"task": task})

    @staticmethod
    def _plan_docker(plan: ExecutionPlan, task: str) -> None:
        plan.objective = "Operación Docker"
        ExecutionPlanner._set_execution_unit(plan, "skill", "sandbox", {"task": task})

    @staticmethod
    def _plan_default(plan: ExecutionPlan, task: str) -> None:
        if not plan.intent:
            plan.intent = "conversation"
        plan.objective = task
        ExecutionPlanner._set_execution_unit(plan, "agent", "task_agent", {"task": task})
