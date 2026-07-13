from __future__ import annotations

import logging

from core.config import Config

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selecciona el proveedor LLM preferido según la skill detectada.

    ProviderSelector únicamente determina el proveedor preferido.
    ProviderManager sigue siendo responsable de ejecutar el provider
    y aplicar fallback cuando sea necesario.
    """

    CODE_SKILLS = {
        "analyze",
        "analyze_code",
        "code",
        "create_project",
    }

    ARCHITECTURE_SKILLS = {
        "analyze_project",
    }

    DOCUMENTATION_SKILLS = {
        "readme",
    }

    @classmethod
    def select(
        cls,
        task: str,
        skill_name: str | None = None,
        requested_provider: str | None = None,
    ) -> str:
        """
        Determina el proveedor preferido.

        Prioridad:
        1. Provider solicitado explícitamente.
        2. Provider configurado para la skill.
        3. Provider por defecto.
        """

        if requested_provider:
            provider = requested_provider.strip().lower()

            logger.info(
                "Provider solicitado explícitamente: %s",
                provider,
            )

            return provider

        provider = cls._select_for_skill(
            skill_name=skill_name,
        )

        logger.info(
            "Provider seleccionado para skill '%s': %s",
            skill_name or "general",
            provider,
        )

        return provider

    @classmethod
    def _select_for_skill(
        cls,
        skill_name: str | None,
    ) -> str:
        if not skill_name:
            return Config.DEFAULT_PROVIDER

        normalized_skill = skill_name.strip().lower()

        if normalized_skill in cls.ARCHITECTURE_SKILLS:
            return Config.ARCHITECTURE_PROVIDER

        if normalized_skill in cls.CODE_SKILLS:
            return Config.CODE_PROVIDER

        if normalized_skill in cls.DOCUMENTATION_SKILLS:
            return getattr(
                Config,
                "DOCUMENTATION_PROVIDER",
                Config.DEFAULT_PROVIDER,
            )

        return Config.DEFAULT_PROVIDER