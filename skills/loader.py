from __future__ import annotations

import importlib
import logging

from skills.base import Skill
from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Descubre y registra Skills.

    Responsabilidades:

    - Importar módulos.
    - Registrar clases Skill.
    - Inicializar catálogo.

    No:

    - Ejecuta skills.
    - Decide ejecución.
    - Gestiona planes.
    """

    def __init__(
        self,
        registry: SkillRegistry,
    ):

        self.registry = registry

    # ======================================================
    # Module loading
    # ======================================================

    def load_module(
        self,
        module_path: str,
    ) -> None:

        try:

            module = importlib.import_module(
                module_path,
            )

            self._register_from_module(
                module,
            )

        except Exception:

            logger.exception(
                "Error cargando módulo skill=%s",
                module_path,
            )

    def _register_from_module(
        self,
        module,
    ) -> None:

        for attribute_name in dir(module):

            attribute = getattr(
                module,
                attribute_name,
            )

            if not isinstance(
                attribute,
                type,
            ):
                continue

            if not issubclass(
                attribute,
                Skill,
            ):
                continue

            if attribute is Skill:
                continue

            # Evita registrar clases importadas
            if attribute.__module__ != module.__name__:
                continue

            skill_name = getattr(
                attribute,
                "name",
                None,
            )

            if not skill_name:
                continue

            self.registry.register(
                skill_name,
                attribute,
            )

            logger.info(
                "Skill registrada=%s",
                skill_name,
            )

    # ======================================================
    # Defaults
    # ======================================================

    def load_defaults(
        self,
    ) -> None:

        modules = [
            "skills.code.analyze",
            "skills.code.executor",
            "skills.code.generate",
            "skills.code.project_analyzer",
            "skills.code.sandbox",
        ]

        for module in modules:

            self.load_module(
                module,
            )
