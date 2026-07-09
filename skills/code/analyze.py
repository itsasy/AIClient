from skills.base import Skill


class AnalyzeCodeSkill(Skill):

    name = "analyze"

    description = "Analiza código"

    def execute(self, code_snippet="", language="python", **kwargs):
        return {
            "type": "code_analysis",
            "payload": {
                "code": code_snippet,
                "language": language,
            },
        }