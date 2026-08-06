from __future__ import annotations

import logging

from skills.registry import SkillRegistry
from skills.loader import SkillLoader

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Resolver central de Skills.

    Responsabilidades:

    - Resolver Skills registradas.
    - Inicializar catálogo.
    - Exponer información.

    No:

    - Ejecuta Skills.
    - Maneja retries.
    - Normaliza resultados.

    La ejecución pertenece a SkillRuntime.
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        auto_load: bool = True,
    ):

        self.registry = registry or SkillRegistry()

        self.loader = SkillLoader(
            self.registry,
        )

        if auto_load:

            self.loader.load_defaults()

    # ======================================================
    # Resolution
    # ======================================================

    def get(
        self,
        skill_name: str,
    ):

        if not skill_name:

            return None

        return self.registry.get(
            skill_name,
        )

    # ======================================================
    # Information
    # ======================================================

    def has(
        self,
        skill_name: str,
    ) -> bool:

        return self.registry.has(
            skill_name,
        )

    def list(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded(
        self,
    ) -> list[str]:

        return self.registry.loaded()

    def metadata(
        self,
    ) -> list[dict]:

        return self.registry.metadata()

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        result = {}

        for name in self.registry.list():

            skill = self.registry.get(
                name,
            )

            if skill:

                result[name] = skill.capabilities

        return result
