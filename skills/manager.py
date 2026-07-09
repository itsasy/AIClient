from skills.docs.readme import GenerateReadmeSkill
from skills.code.generate import GenerateCodeSkill
from skills.code.analyze import AnalyzeCodeSkill
from skills.code.project_analyzer import ProjectAnalyzerSkill
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
    
    def execute(self, skill_name: str, **kwargs):
        if skill_name in self.skills:
            return self.skills[skill_name].execute(**kwargs)
        return f"Skill '{skill_name}' no encontrada. Skills disponibles: {list(self.skills.keys())}"
