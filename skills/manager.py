from __future__ import annotations

import logging

from skills.registry import SkillRegistry
from skills.loader import SkillLoader

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Resolver central de Skills.

    No conoce implementaciones concretas.
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        loader: SkillLoader | None = None,
    ):

        self.registry = registry or SkillRegistry()

        self.loader = loader or SkillLoader(self.registry)

        self.loader.load_defaults()

    def get(
        self,
        skill_name: str,
    ):

        skill = self.registry.get(skill_name)

        if skill is None:

            logger.warning(
                "Skill inexistente=%s",
                skill_name,
            )

        return skill

    def execute(
        self,
        skill_name: str,
        **kwargs,
    ):

        skill = self.get(skill_name)

        if skill is None:

            raise ValueError(f"Skill '{skill_name}' no registrada")

        logger.info(
            "Ejecutando skill=%s",
            skill_name,
        )

        result = skill.execute(**kwargs)

        return self.normalize(result)

    def normalize(
        self,
        result,
    ):

        if isinstance(
            result,
            dict,
        ):

            return result

        return {
            "ok": True,
            "result": result,
            "error": None,
        }

    def list(self):

        return self.registry.list()

    def has(
        self,
        skill_name: str,
    ):

        return self.registry.has(skill_name)
