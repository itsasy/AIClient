from __future__ import annotations

import importlib
import logging

from skills.base import Skill

from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Descubrimiento y registro de Skills.
    """

    def __init__(
        self,
        registry: SkillRegistry,
    ):

        self.registry = registry

    # ==========================================================
    # Module loading
    # ==========================================================

    def load_module(
        self,
        module_path: str,
    ):

        try:

            module = importlib.import_module(
                module_path,
            )

            self._register_from_module(
                module,
            )

        except Exception:

            logger.exception(
                "Error cargando módulo=%s",
                module_path,
            )

    def _register_from_module(
        self,
        module,
    ):

        for name in dir(module):

            obj = getattr(
                module,
                name,
            )

            if not isinstance(
                obj,
                type,
            ):
                continue

            if not issubclass(
                obj,
                Skill,
            ):
                continue

            if obj is Skill:
                continue

            if obj.__module__ != module.__name__:
                continue

            skill_name = getattr(
                obj,
                "name",
                None,
            )

            if not skill_name:
                continue

            self.registry.register(
                skill_name,
                obj,
            )

            logger.info(
                "Skill cargada=%s capabilities=%s",
                skill_name,
                getattr(
                    obj,
                    "capabilities",
                    [],
                ),
            )

    # ==========================================================
    # Defaults
    # ==========================================================

    def load_defaults(
        self,
    ):

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
