from __future__ import annotations

import logging
from typing import ClassVar

from core.config import Config
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selecciona el proveedor LLM y su cadena de fallback.

    Responsabilidades:
        - Resolver el proveedor preferido.
        - Resolver la categoría del plan.
        - Obtener proveedor/fallbacks desde Config.
        - Normalizar la cadena de fallback.

    No:
        - Construye prompts.
        - Ejecuta proveedores.
        - Modifica el ExecutionPlan.
        - Decide qué agente o skill ejecutar.

    Prioridad de selección:

        1. preferred_provider explícito
        2. intent_category
        3. execution_unit_type
        4. execution_mode
        5. default
    """

    CATEGORY_MAP: ClassVar[dict[str, tuple[str, list[str]]]] = {
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

    CATEGORY_ALIASES: ClassVar[dict[str, str]] = {
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
        """
        Selecciona proveedor y fallback chain para un plan.

        Returns:
            tuple[str, list[str]]:
                proveedor principal y proveedores fallback.
        """

        if plan is None:
            raise ValueError("plan no puede ser None.")

        # --------------------------------------------------
        # 1. Provider explícito
        # --------------------------------------------------

        preferred = cls._get_preferred_provider(plan)

        if preferred:
            fallbacks = cls._clean_chain(
                preferred,
                Config.DEFAULT_FALLBACKS,
            )

            logger.info(
                "Provider explícito seleccionado | provider=%s | fallbacks=%s",
                preferred,
                fallbacks,
            )

            return preferred, fallbacks

        # --------------------------------------------------
        # 2. Resolver categoría
        # --------------------------------------------------

        category = cls._resolve_category(plan)

        provider, fallbacks = cls.CATEGORY_MAP.get(
            category,
            (
                Config.DEFAULT_PROVIDER,
                Config.DEFAULT_FALLBACKS,
            ),
        )

        provider = cls._normalize_provider(provider)

        fallbacks = cls._clean_chain(
            provider,
            fallbacks,
        )

        logger.info(
            "Provider seleccionado | provider=%s | category=%s | fallbacks=%s",
            provider,
            category,
            fallbacks,
        )

        return provider, fallbacks

    # ======================================================
    # Provider
    # ======================================================

    @classmethod
    def _get_preferred_provider(
        cls,
        plan: ExecutionPlan,
    ) -> str | None:

        preferred = plan.metadata.get("preferred_provider")

        if preferred is None:
            return None

        normalized = cls._normalize_provider(str(preferred))

        return normalized or None

    @staticmethod
    def _normalize_provider(
        provider: str,
    ) -> str:

        return provider.strip().lower()

    # ======================================================
    # Category resolution
    # ======================================================

    @classmethod
    def _resolve_category(
        cls,
        plan: ExecutionPlan,
    ) -> str:

        # 1. Intent category
        category = cls._category_from_intent(
            plan.intent_category,
        )

        if category:
            return category

        # 2. Execution unit
        category = cls._category_from_unit(
            plan.execution_unit_type,
        )

        if category:
            return category

        # 3. Execution mode
        category = cls._category_from_mode(
            plan,
        )

        if category:
            return category

        # 4. Default
        return "fast"

    @classmethod
    def _category_from_intent(
        cls,
        intent_category: str | None,
    ) -> str | None:

        if not intent_category:
            return None

        normalized = str(intent_category).strip().lower()

        normalized = cls.CATEGORY_ALIASES.get(
            normalized,
            normalized,
        )

        if normalized not in cls.CATEGORY_MAP:
            logger.debug(
                "Intent category no reconocida=%s",
                normalized,
            )
            return None

        return normalized

    @staticmethod
    def _category_from_unit(
        unit_type: str | None,
    ) -> str | None:

        if not unit_type:
            return None

        normalized = str(unit_type).strip().lower()

        if normalized == "skill":
            return "code"

        if normalized == "agent":
            return "architecture"

        return None

    @staticmethod
    def _category_from_mode(
        plan: ExecutionPlan,
    ) -> str | None:

        if plan.is_multi_step():
            return "architecture"

        return None

    # ======================================================
    # Fallback chain
    # ======================================================

    @classmethod
    def _clean_chain(
        cls,
        provider: str,
        chain: list[str] | tuple[str, ...] | None,
    ) -> list[str]:

        normalized_provider = cls._normalize_provider(
            provider,
        )

        if not chain:
            return []

        clean: list[str] = []

        for item in chain:

            if item is None:
                continue

            normalized = cls._normalize_provider(str(item))

            if not normalized:
                continue

            if normalized == normalized_provider:
                continue

            if normalized in clean:
                continue

            clean.append(normalized)

        return clean
