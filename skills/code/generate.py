from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill


class GenerateCodeSkill(Skill):

    name = "generate"

    description = "Prepara solicitudes estructuradas de generación de código."

    version = "2.0"

    capabilities = (
        "code_generation",
        "task_translation",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        task = params.get(
            "task",
            "",
        )

        language = params.get(
            "language",
            "python",
        )

        framework = params.get(
            "framework",
        )

        filepath = params.get(
            "filepath",
        )

        if not task.strip():

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó una tarea de generación.",
            }

        return {
            "ok": True,
            "result": {
                "type": "code_generation",
                "request": {
                    "task": task,
                    "language": language,
                    "framework": framework,
                    "filepath": filepath,
                },
            },
            "error": None,
        }
