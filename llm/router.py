import logging

from core.execution_plan import ExecutionPlan

from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Responsable únicamente de comunicarse con los modelos LLM.

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

        provider, fallbacks = ProviderSelector.select(
            plan,
        )

        logger.info(
            "LLM Router | provider=%s | skill=%s | intent=%s",
            provider,
            plan.skill,
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
