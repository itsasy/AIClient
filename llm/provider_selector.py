import logging

from core.config import Config
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selecciona proveedor LLM según ExecutionPlan.

    Prioridad:
        1. preferred_provider en metadata (si existe)
        2. intent_category
        3. execution_unit_type (agent → architecture, skill → code, etc.)
        4. execution_mode (multi_step → architecture)
        5. default
    """

    CATEGORY_MAP = {
        "code": (Config.CODE_PROVIDER, Config.CODE_FALLBACKS),
        "architecture": (Config.ARCHITECTURE_PROVIDER, Config.ARCHITECTURE_FALLBACKS),
        "documentation": (
            getattr(Config, "DOCUMENTATION_PROVIDER", Config.DEFAULT_PROVIDER),
            getattr(Config, "DOCUMENTATION_FALLBACKS", Config.DEFAULT_FALLBACKS),
        ),
        "fast": (
            getattr(Config, "FAST_PROVIDER", Config.DEFAULT_PROVIDER),
            getattr(Config, "FAST_FALLBACKS", Config.DEFAULT_FALLBACKS),
        ),
    }

    CATEGORY_ALIASES = {
        "project": "architecture",
        "planning": "architecture",
        "analysis": "architecture",
        "execution": "code",
        "file": "code",
        "conversation": "fast",
    }

    @classmethod
    def select(cls, plan: ExecutionPlan) -> tuple[str, list[str]]:
        # 1. Provider forzado desde metadata
        if plan.metadata.get("preferred_provider"):
            provider = plan.metadata["preferred_provider"].lower()
            logger.info("Provider forzado: %s", provider)
            return provider, cls._clean_chain(provider, Config.DEFAULT_FALLBACKS)

        # 2. Determinar categoría desde intent_category
        category = None
        if plan.intent_category:
            category = cls.CATEGORY_ALIASES.get(
                plan.intent_category.lower(), plan.intent_category.lower()
            )

        # 3. Si no, desde execution_unit_type
        if category is None and plan.execution_unit_type:
            if plan.execution_unit_type == "agent":
                category = "architecture"
            elif plan.execution_unit_type == "skill":
                category = "code"
            else:
                category = "fast"

        # 4. Si no, desde execution_mode
        if category is None and plan.is_multi_step():
            category = "architecture"

        # 5. Fallback
        if category is None:
            category = "fast"

        provider, fallbacks = cls.CATEGORY_MAP.get(
            category, (Config.DEFAULT_PROVIDER, Config.DEFAULT_FALLBACKS)
        )

        logger.info(
            "Provider=%s | Category=%s | unit=%s:%s",
            provider,
            category,
            plan.execution_unit_type,
            plan.execution_unit,
        )

        return provider, cls._clean_chain(provider, fallbacks)

    @staticmethod
    def _clean_chain(provider: str, chain: list[str]) -> list[str]:
        clean = []
        for item in chain:
            item = item.lower()
            if item == provider:
                continue
            if item not in clean:
                clean.append(item)
        return clean
