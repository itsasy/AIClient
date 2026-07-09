from skills.code.analyze import AnalyzeCodeSkill
from skills.code.generate import GenerateCodeSkill
from skills.code.project_analyzer import ProjectAnalyzerSkill
from skills.docs.readme import GenerateReadmeSkill
from skills.tools.shell import ShellTool


class SkillManager:

    def __init__(self):

        self.skills = {
            "readme": GenerateReadmeSkill(),
            "code": GenerateCodeSkill(),
            "analyze": AnalyzeCodeSkill(),
            "analyze_project": ProjectAnalyzerSkill(),
            "shell": ShellTool(),
        }

    def execute(self, skill_name, **kwargs):

        skill = self.skills.get(skill_name)

        if skill is None:
            raise ValueError(f"Skill '{skill_name}' no encontrada")

        return skill.execute(**kwargs)