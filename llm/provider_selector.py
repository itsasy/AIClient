import logging

from core.config import Config
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selecciona el proveedor LLM adecuado para un ExecutionPlan.

    Prioridad:

        preferred_provider
                ↓
        intent_category
                ↓
             skill
                ↓
        execution_mode
                ↓
            default
    """

    CATEGORY_MAP = {
        "code": (
            Config.CODE_PROVIDER,
            Config.CODE_FALLBACKS,
        ),
        "architecture": (
            Config.ARCHITECTURE_PROVIDER,
            Config.ARCHITECTURE_FALLBACKS,
        ),
        "documentation": (
            getattr(
                Config,
                "DOCUMENTATION_PROVIDER",
                Config.DEFAULT_PROVIDER,
            ),
            getattr(
                Config,
                "DOCUMENTATION_FALLBACKS",
                Config.DEFAULT_FALLBACKS,
            ),
        ),
        "fast": (
            getattr(
                Config,
                "FAST_PROVIDER",
                Config.DEFAULT_PROVIDER,
            ),
            getattr(
                Config,
                "FAST_FALLBACKS",
                Config.DEFAULT_FALLBACKS,
            ),
        ),
    }

    SKILL_CATEGORY = {
        # -------------------------
        # Código
        # -------------------------
        "code": "code",
        "execute_code": "code",
        "sandbox": "code",
        "refactor_code": "code",
        "analyze_code": "code",
        # -------------------------
        # Arquitectura
        # -------------------------
        "plan": "architecture",
        "architecture": "architecture",
        "analyze_project": "architecture",
        "reflection": "architecture",
        "self_critic": "architecture",
        "critique": "architecture",
        # -------------------------
        # Documentación
        # -------------------------
        "readme": "documentation",
        "generate_proposal": "documentation",
        # -------------------------
        # Conversación
        # -------------------------
        "conversation": "fast",
        "chat": "fast",
        "general": "fast",
        "quick": "fast",
        # -------------------------
        # Aprendizaje
        # -------------------------
        "learning": "fast",
    }

    @classmethod
    def select(
        cls,
        plan: ExecutionPlan,
    ) -> tuple[str, list[str]]:

        # =====================================================
        # Provider forzado
        # =====================================================

        if plan.preferred_provider:

            provider = plan.preferred_provider.lower()

            logger.info(
                "Provider forzado: %s",
                provider,
            )

            return (
                provider,
                cls._clean_chain(
                    provider,
                    Config.DEFAULT_FALLBACKS,
                ),
            )

        # =====================================================
        # Intent category
        # =====================================================

        category = plan.intent_category

        # =====================================================
        # Primera skill del plan
        # =====================================================

        skill = plan.skills[0] if plan.skills else None

        # =====================================================
        # Skill -> Category
        # =====================================================

        if category is None and skill is not None:
            category = cls.SKILL_CATEGORY.get(skill)

        # =====================================================
        # MultiStep
        # =====================================================

        if category is None and plan.execution_mode == "multi_step":
            category = "architecture"

        # =====================================================
        # Default
        # =====================================================

        if category is None:
            category = "fast"

        provider, fallbacks = cls.CATEGORY_MAP.get(
            category,
            (
                Config.DEFAULT_PROVIDER,
                Config.DEFAULT_FALLBACKS,
            ),
        )

        logger.info(
            "Provider=%s | Category=%s | Skill=%s",
            provider,
            category,
            skill,
        )

        return (
            provider,
            cls._clean_chain(
                provider,
                fallbacks,
            ),
        )

    @staticmethod
    def _clean_chain(
        provider: str,
        chain: list[str],
    ) -> list[str]:

        clean = []

        for item in chain:

            if item == provider:
                continue

            if item not in clean:
                clean.append(item)

        return clean
