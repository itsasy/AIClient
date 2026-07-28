from __future__ import annotations

import logging

from core.config import Config

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selecciona el proveedor LLM y la cadena de fallbacks según el tipo de tarea.

    Categorías:
    - Código: generación, análisis, refactor
    - Arquitectura: análisis de proyectos, planificación, SDD, Self-Critic
    - Documentación: README, propuestas
    - Rápido: consultas simples, chat
    - General: resto de tareas
    """

    # Skills que requieren precisión en código
    CODE_SKILLS = {
        "analyze",
        "analyze_code",
        "code",
        "create_project",
        "execute_code",
        "sandbox",
        "refactor_code",
    }

    # Skills que requieren razonamiento profundo
    ARCHITECTURE_SKILLS = {
        "analyze_project",
        "plan",
        "reflection",
        "self_critic",
        "critique",
        "architecture",
    }

    # Skills de documentación
    DOCUMENTATION_SKILLS = {
        "readme",
        "generate_proposal",
    }

    # Skills rápidas (consultas simples)
    FAST_SKILLS = {
        "general",
        "chat",
        "quick",
    }

    @classmethod
    def select(
        cls,
        task: str,
        skill_name: str | None = None,
        requested_provider: str | None = None,
    ) -> tuple[str, list[str]]:
        """
        Determina el proveedor primario y la cadena de fallbacks.

        Prioridad:
        1. Proveedor solicitado explícitamente (por CLI o parámetro).
        2. Proveedor configurado para la categoría de la skill.
        3. Proveedor por defecto.

        Returns:
            tuple[str, list[str]]: (proveedor_primario, lista_de_fallbacks)
        """
        # 1. Si se solicita un proveedor específico, usarlo
        if requested_provider:
            primary = requested_provider.strip().lower()
            # Obtener fallbacks según la skill (o por defecto)
            fallbacks = cls._get_fallbacks_for_skill(skill_name)
            return primary, fallbacks

        # 2. Detectar la categoría según la skill
        if skill_name:
            normalized_skill = skill_name.strip().lower()

            if normalized_skill in cls.CODE_SKILLS:
                primary = Config.CODE_PROVIDER
                fallbacks = Config.CODE_FALLBACKS
            elif normalized_skill in cls.ARCHITECTURE_SKILLS:
                primary = Config.ARCHITECTURE_PROVIDER
                fallbacks = Config.ARCHITECTURE_FALLBACKS
            elif normalized_skill in cls.DOCUMENTATION_SKILLS:
                primary = getattr(
                    Config, "DOCUMENTATION_PROVIDER", Config.DEFAULT_PROVIDER
                )
                fallbacks = getattr(
                    Config, "DEFAULT_FALLBACKS", Config.FALLBACK_PROVIDERS
                )
            elif normalized_skill in cls.FAST_SKILLS:
                primary = getattr(Config, "FAST_PROVIDER", Config.DEFAULT_PROVIDER)
                fallbacks = getattr(Config, "FAST_FALLBACKS", Config.FALLBACK_PROVIDERS)
            else:
                primary = Config.DEFAULT_PROVIDER
                fallbacks = Config.DEFAULT_FALLBACKS
        else:
            # Sin skill, usar valores por defecto
            primary = Config.DEFAULT_PROVIDER
            fallbacks = Config.DEFAULT_FALLBACKS

        # Asegurar que el primario no esté duplicado en fallbacks
        fallbacks = [p for p in fallbacks if p != primary]

        logger.info(
            "Seleccionado | skill=%s | primary=%s | fallbacks=%s",
            skill_name or "general",
            primary,
            fallbacks,
        )

        return primary, fallbacks

    @classmethod
    def _get_fallbacks_for_skill(cls, skill_name: str | None) -> list[str]:
        """Obtiene los fallbacks por defecto según la skill."""
        if not skill_name:
            return Config.DEFAULT_FALLBACKS

        normalized_skill = skill_name.strip().lower()

        if normalized_skill in cls.CODE_SKILLS:
            return Config.CODE_FALLBACKS
        if normalized_skill in cls.ARCHITECTURE_SKILLS:
            return Config.ARCHITECTURE_FALLBACKS
        if normalized_skill in cls.FAST_SKILLS:
            return getattr(Config, "FAST_FALLBACKS", Config.FALLBACK_PROVIDERS)

        return Config.DEFAULT_FALLBACKS
