from typing import Any

from skills.base import Skill


class GenerateCodeSkill(Skill):

    name = "code"

    description = "Solicita generación de código al agente desarrollador."

    def execute(
        self,
        task: str,
        language: str = "python",
        framework: str | None = None,
        filepath: str | None = None,
        **kwargs: Any,
    ):

        return {
            "type": "code_generation",
            "payload": {
                "task": task,
                "language": language,
                "framework": framework,
                "filepath": filepath,
            },
        }
