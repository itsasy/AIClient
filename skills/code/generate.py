from __future__ import annotations

from typing import Any

from skills.base import Skill


class GenerateCodeSkill(Skill):

    name = "generate"

    description = "Prepara una solicitud estructurada " "de generación de código."

    version = "1.0"

    def execute(
        self,
        task: str = "",
        language: str = "python",
        framework: str | None = None,
        filepath: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:

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
