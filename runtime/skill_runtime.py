from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan

from skills.registry import SkillRegistry
from skills.loader import SkillLoader
from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRuntime:
    """
    Runtime central de Skills.

    Flujo:

        ExecutionPlan
              |
              v
        SkillRuntime
              |
              v
        SkillRegistry
              |
              v
        Skill
              |
              v
        execute()


    Responsabilidades:

    - Resolver skills.
    - Ejecutar skills.
    - Gestionar lifecycle.
    - Capturar errores.
    - Exponer métricas.


    No:

    - Decide qué skill utilizar.
    - Construye planes.
    - Analiza intención.
    - Gestiona agentes.
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        loader: SkillLoader | None = None,
    ):

        self.registry = registry or SkillRegistry()

        self.loader = loader or SkillLoader(
            self.registry,
        )

        self.loader.load_defaults()

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
        }

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        name: str,
        factory: type[Skill],
    ) -> None:
        """
        Permite registrar skills externas.
        """

        self.registry.register(
            name,
            factory,
        )

    # ==========================================================
    # Execute
    # ==========================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        context = context or {}

        if not plan.skills:

            return {
                "ok": False,
                "error": "ExecutionPlan sin skills",
            }

        results = []

        for skill_name in plan.skills:

            result = self._execute_skill(
                skill_name,
                plan,
                context,
            )

            results.append(
                result,
            )

        success = all(item.get("ok", False) for item in results)

        return {
            "ok": success,
            "skills": results,
        }

    def _execute_skill(
        self,
        skill_name: str,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        skill = self._resolve(
            skill_name,
        )

        if skill is None:

            self.metrics["failed"] += 1

            return {
                "skill": skill_name,
                "ok": False,
                "error": "Skill no encontrada",
            }

        try:

            validation_errors = skill.validate(
                **plan.params,
            )

            if validation_errors:

                self.metrics["failed"] += 1

                return {
                    "skill": skill_name,
                    "ok": False,
                    "error": validation_errors,
                }

            params = {}

            params.update(
                context,
            )

            params.update(
                plan.params,
            )

            params.update(
                plan.execution_context,
            )

            result = skill.execute(
                **params,
            )

            self.metrics["executions"] += 1

            self.metrics["success"] += 1

            return {
                "skill": skill_name,
                "ok": True,
                "result": result,
            }

        except Exception as exc:

            self.metrics["failed"] += 1

            logger.exception(
                "Error ejecutando skill=%s",
                skill_name,
            )

            return {
                "skill": skill_name,
                "ok": False,
                "error": str(exc),
            }

    # ==========================================================
    # Resolve
    # ==========================================================

    def _resolve(
        self,
        name: str,
    ) -> Skill | None:

        return self.registry.get(
            name,
        )

    # ==========================================================
    # Information
    # ==========================================================

    def list_skills(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded_skills(
        self,
    ) -> list[str]:

        return self.registry.loaded()

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()

    def get_skill(
        self,
        name: str,
    ) -> Skill | None:

        return self.registry.get(name)
