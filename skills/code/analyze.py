from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class AnalyzeCodeSkill(Skill):

    name = "analyze"

    description = "Analiza código fuente y devuelve información estructurada."

    version = "2.0"

    capabilities = (
        "code_analysis",
        "static_analysis",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        code_snippet = params.get(
            "code_snippet",
            params.get("code", ""),
        )

        language = params.get(
            "language",
            "python",
        )

        if not code_snippet.strip():

            return {
                "ok": False,
                "result": None,
                "error": ("No se proporcionó código " "para analizar."),
            }

        return {
            "ok": True,
            "result": {
                "type": "code_analysis",
                "language": language,
                "code": code_snippet,
                "analysis": {
                    "lines": len(code_snippet.splitlines()),
                    "characters": len(code_snippet),
                },
            },
            "error": None,
        }
