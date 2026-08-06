from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class CodeRefactorSkill(Skill):

    name = "refactor_code"

    description = "Refactoriza código a estándares modernos."

    version = "2.0"

    capabilities = (
        "code_refactoring",
        "clean_code",
        "architecture_improvement",
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
            "",
        )

        if not code:

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó código.",
            }

        return {
            "ok": True,
            "result": {
                "type": "refactor",
                "payload": {
                    "code": code,
                    "standards": (
                        standards or ("Clean Code, SOLID, tipado, " "manejo de errores, Laravel 11")
                    ),
                },
            },
            "error": None,
        }
