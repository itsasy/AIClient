from skills.base import Skill


class AnalyzeCodeSkill(Skill):

    name = "analyze"

    description = "Analiza código"

    def execute(self, code_snippet="", language="python", **kwargs):

        return {

            "analysis": "code",

            "language": language,

            "code": code_snippet
        }