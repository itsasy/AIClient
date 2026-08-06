from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class CodeRefactorSkill(Skill):

    name = "refactor_code"

    description = "Prepara solicitudes estructuradas " "de refactorización de código."

    version = "2.0"

    capabilities = (
        "code_refactoring",
        "clean_code",
        "architecture_review",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        code = params.get(
            "code",
            "",
        )

        standards = params.get(
            "standards",
            ("Clean Code, SOLID, tipado, " "manejo de errores, Laravel 11"),
        )

        if not code.strip():

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó código.",
            }

        return {
            "ok": True,
            "result": {
                "type": "refactor",
                "code": code,
                "standards": standards,
            },
            "error": None,
        }
