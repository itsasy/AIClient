from skills.base import Skill


class CodeRefactorSkill(Skill):
    name = "refactor_code"
    description = "Refactoriza código a estándares modernos"

    def execute(self, code: str, standards: str = "", **kwargs):
        return {
            "type": "refactor",
            "payload": {
                "code": code,
                "standards": standards
                or "Clean Code, SOLID, tipado, manejo de errores, Laravel 11",
            },
        }
