from skills.code.analyze import AnalyzeCodeSkill
from skills.code.generate import GenerateCodeSkill
from skills.code.executor import CodeExecutorSkill
from skills.code.project_analyzer import ProjectAnalyzerSkill
from skills.docs.readme import GenerateReadmeSkill
from skills.tools.shell import ShellTool
from skills.tools.docker import DockerTool

class SkillManager:
    def __init__(self):
        self.skills = {
            "readme": GenerateReadmeSkill(),
            "code": GenerateCodeSkill(),
            "analyze": AnalyzeCodeSkill(),
            "analyze_project": ProjectAnalyzerSkill(),
            "shell": ShellTool(),
            "execute_code": CodeExecutorSkill(),
            "docker": DockerTool(),
        }

    def execute(self, skill_name: str, **kwargs):
        skill = self.skills.get(skill_name)

        if skill is None:
            available = ", ".join(self.skills.keys())
            raise ValueError(
                f"Skill '{skill_name}' no encontrada. "
                f"Disponibles: {available}"
            )

        return skill.execute(**kwargs)