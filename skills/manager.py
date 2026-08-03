import logging

from skills.projects.laravel import LaravelProjectSkill
from skills.projects.full_generator import FullProjectGeneratorSkill

from skills.code.project_analyzer import ProjectAnalyzerSkill
from skills.code.generate import GenerateCodeSkill
from skills.code.executor import CodeExecutorSkill
from skills.code.sandbox import CodeSandboxSkill
from skills.code.analyze import AnalyzeCodeSkill

from skills.docs.readme import GenerateReadmeSkill

from skills.knowledge.ingest import IngestDocumentSkill

from skills.tools.docker import DockerTool
from skills.tools.shell import ShellTool
from skills.tools.write_file import WriteFileSkill

logger = logging.getLogger(__name__)


class SkillManager:

    def __init__(self):

        self.skills = {
            "readme": GenerateReadmeSkill(),
            "code": GenerateCodeSkill(),
            "analyze": AnalyzeCodeSkill(),
            "analyze_project": ProjectAnalyzerSkill(),
            "execute_code": CodeExecutorSkill(),
            "sandbox": CodeSandboxSkill(),
            "shell": ShellTool(),
            "docker": DockerTool(),
            "laravel_project": LaravelProjectSkill(),
            "full_project": FullProjectGeneratorSkill(),
            "ingest": IngestDocumentSkill(),
            "write_file": WriteFileSkill(),
        }

    def execute(
        self,
        skill_name: str,
        **kwargs,
    ):

        skill = self.skills.get(skill_name)

        if skill is None:

            raise ValueError(f"Skill '{skill_name}' no encontrada.")

        logger.info(
            "Skill -> %s",
            skill_name,
        )

        result = skill.execute(
            **kwargs,
        )

        return self._normalize(
            result,
        )

    def _normalize(
        self,
        result,
    ):

        if isinstance(
            result,
            dict,
        ):
            return result

        return {
            "type": "skill_result",
            "payload": {
                "output": str(result),
            },
        }

    def has(
        self,
        skill_name: str,
    ) -> bool:

        return skill_name in self.skills

    def list(
        self,
    ):

        return sorted(
            self.skills.keys(),
        )
