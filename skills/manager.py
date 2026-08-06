from __future__ import annotations

import logging

from skills.registry import SkillRegistry
from skills.loader import SkillLoader
from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Resolver central de Skills.

    Responsabilidades:

    - Inicializar catálogo.
    - Resolver Skills.
    - Exponer metadata.
    - Gestionar carga.

    No:

    - Ejecuta Skills.
    - Maneja retries.
    - Normaliza resultados.

    La ejecución pertenece a SkillRuntime.
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        loader: SkillLoader | None = None,
        auto_load: bool = True,
    ):

        self.registry = registry or SkillRegistry()

        self.loader = loader or SkillLoader(
            self.registry,
        )

        if auto_load:

            self.load_defaults()

    # ======================================================
    # Loading
    # ======================================================

    def load_defaults(
        self,
    ) -> None:

        self.loader.load_defaults()

    def load_module(
        self,
        module_path: str,
    ) -> None:

        self.loader.load_module(
            module_path,
        )

    # ======================================================
    # Resolution
    # ======================================================

    def get(
        self,
        name: str,
    ) -> Skill | None:

        if not name:

            return None

        return self.registry.get(
            name,
        )

    def has(
        self,
        name: str,
    ) -> bool:

        return self.registry.has(
            name,
        )

    # ======================================================
    # Information
    # ======================================================

    def list(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded(
        self,
    ) -> list[str]:

        return self.registry.loaded()

    def aliases(
        self,
    ) -> dict[str, str]:

        return self.registry.aliases()

    def metadata(
        self,
    ) -> list[dict]:

        return self.registry.metadata()

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        result = {}

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill:

                result[name] = skill.capabilities

        return result

    # ======================================================
    # Management
    # ======================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        self.registry.unregister(
            name,
        )

    def clear(
        self,
    ) -> None:

        self.registry.clear()
