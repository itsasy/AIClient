import logging

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
              │
              ▼
      ProviderSelector
              │
              ▼
       PromptBuilder
              │
              ▼
      ProviderManager
              │
              ▼
            Respuesta
    """

    provider_manager = ProviderManager()

    @classmethod
    def generate(
        cls,
        plan: ExecutionPlan,
        context: dict | None = None,
        **kwargs,
    ) -> str:

        context = context or {}

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
            "LLM Router | provider=%s | skills=%s | intent=%s",
            provider,
            plan.skills,
            plan.intent,
        )

        prompt = PromptBuilder.build(
            plan=plan,
            context=context,
        )

        return cls.provider_manager.generate(
            prompt=prompt,
            provider_name=provider,
            fallback_chain=fallbacks,
            **kwargs,
        )
