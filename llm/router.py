from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Punto único de comunicación con proveedores LLM.

    Flujo:

        ExecutionPlan
            ↓
        ProviderSelector
            ↓
        PromptBuilder
            ↓
        ProviderManager
            ↓
        Provider
    """

    def __init__(
        self,
        provider_manager: ProviderManager | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.provider_manager = provider_manager or ProviderManager()

        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:

        context = dict(context or {})

        try:
            provider, fallbacks = ProviderSelector.select(
                plan,
            )

        except Exception:
            logger.exception(
                "Error seleccionando proveedor LLM",
            )
            raise

        logger.info(
            "LLM Router | provider=%s | unit=%s:%s | intent=%s | steps=%s",
            provider,
            plan.execution_unit_type,
            plan.execution_unit,
            plan.intent,
            len(plan.steps) if plan.steps else 0,
        )

        prompt_builder = PromptBuilder()

        prompt = prompt_builder.build(
            plan=plan,
            context=context,
        )

        return self.provider_manager.generate(
            prompt=prompt,
            provider_name=provider,
            fallback_chain=fallbacks,
            **kwargs,
        )
