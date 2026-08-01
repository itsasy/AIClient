from typing import Any

from skills.base import Skill


class GenerateCodeSkill(Skill):

    name = "code"

    description = "Genera instrucciones de código para el agente desarrollador."

    def execute(
        self,
        task: str = "",
        language: str = "python",
        **kwargs: Any,
    ) -> dict:

        return {
            "type": "code_generation",
            "payload": {
                "task": task,
                "language": language,
            },
        }
