from __future__ import annotations

import logging

from core.config import Config
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selecciona proveedor LLM según ExecutionPlan.

    Prioridad:

        1. preferred_provider
        2. intent_category reconocida
        3. execution_unit_type
        4. execution_mode
        5. default
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

    CATEGORY_ALIASES = {
        "project": "architecture",
        "planning": "architecture",
        "analysis": "architecture",
        "execution": "code",
        "file": "code",
        "conversation": "fast",
    }

    @classmethod
    def select(
        cls,
        plan: ExecutionPlan,
    ) -> tuple[str, list[str]]:

        # ======================================================
        # 1. Provider explícito
        # ======================================================

        preferred = plan.metadata.get(
            "preferred_provider",
        )

        if preferred:
            provider = (
                str(
                    preferred,
                )
                .lower()
                .strip()
            )

            logger.info(
                "Provider forzado=%s",
                provider,
            )

            return (
                provider,
                cls._clean_chain(
                    provider,
                    Config.DEFAULT_FALLBACKS,
                ),
            )

        # ======================================================
        # 2. Intent category
        # ======================================================

        category = cls._category_from_intent(
            plan.intent_category,
        )

        # ======================================================
        # 3. Execution unit
        # ======================================================

        if category is None:
            category = cls._category_from_unit(
                plan.execution_unit_type,
            )

        # ======================================================
        # 4. Execution mode
        # ======================================================

        if category is None:
            category = cls._category_from_mode(
                plan,
            )

        # ======================================================
        # 5. Default
        # ======================================================

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
            "Provider=%s | category=%s | unit=%s:%s",
            provider,
            category,
            plan.execution_unit_type,
            plan.execution_unit,
        )

        return (
            provider,
            cls._clean_chain(
                provider,
                fallbacks,
            ),
        )

    @classmethod
    def _category_from_intent(
        cls,
        intent_category: str | None,
    ) -> str | None:

        if not intent_category:
            return None

        normalized = intent_category.lower().strip()

        normalized = cls.CATEGORY_ALIASES.get(
            normalized,
            normalized,
        )

        if normalized not in cls.CATEGORY_MAP:
            return None

        return normalized

    @staticmethod
    def _category_from_unit(
        unit_type: str | None,
    ) -> str | None:

        if not unit_type:
            return None

        normalized = unit_type.lower().strip()

        if normalized == "agent":
            return "architecture"

        if normalized == "skill":
            return "code"

        return "fast"

    @staticmethod
    def _category_from_mode(
        plan: ExecutionPlan,
    ) -> str | None:

        if plan.is_multi_step():
            return "architecture"

        return None

    @staticmethod
    def _clean_chain(
        provider: str,
        chain: list[str],
    ) -> list[str]:

        clean: list[str] = []

        provider = provider.lower()

        for item in chain:
            item = item.lower()

            if item == provider:
                continue

            if item not in clean:
                clean.append(item)

        return clean
