from __future__ import annotations

import importlib
import logging

from skills.base import Skill
from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Descubre Skills y las registra.

    No ejecuta nada.
    """

    DEFAULT_MODULES = [
        "skills.code.analyze",
        "skills.code.executor",
        "skills.code.generate",
        "skills.code.project_analyzer",
        "skills.code.sandbox",
        "skills.docs.readme",
        "skills.knowledge.ingest",
    ]

    def __init__(
        self,
        registry: SkillRegistry,
    ):

        self.registry = registry

    def load_defaults(self):

        for module in self.DEFAULT_MODULES:

            self.load_module(module)

    def load_module(
        self,
        module_path: str,
    ):

        try:

            module = importlib.import_module(module_path)

            self._register_module(module)

        except Exception:

            logger.exception(
                "Error cargando skills módulo=%s",
                module_path,
            )

    def _register_module(
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
