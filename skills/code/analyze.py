from __future__ import annotations

from typing import Any

from skills.base import Skill


class AnalyzeCodeSkill(Skill):

    name = "analyze"

    description = "Analiza código fuente y devuelve información estructurada."

    version = "1.0"

    capabilities = [
        "code_analysis",
        "static_analysis",
    ]

    def execute(
        self,
        code_snippet: str = "",
        language: str = "python",
        **kwargs: Any,
    ) -> dict[str, Any]:

        if not code_snippet.strip():

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó código para analizar.",
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
