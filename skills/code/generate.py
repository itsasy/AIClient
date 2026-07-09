from skills.base import Skill


class GenerateCodeSkill(Skill):

    name = "code"

    description = "Generador de código"

    def execute(self, task="", language="python", **kwargs):

        return {

            "task": task,

            "language": language
        }