import logging

from core.execution_plan import ExecutionPlan

from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Router responsable únicamente de comunicación con modelos LLM.

    No analiza intención.
    No ejecuta skills.
    No modifica planes.

    Recibe un ExecutionPlan ya preparado.
    """

    provider_manager = ProviderManager()

    @classmethod
    def generate(
        cls,
        plan: ExecutionPlan,
        context: dict | None = None,
        **kwargs,
    ) -> str:
        """
        Genera una respuesta usando el ExecutionPlan.

        Flujo:

        ExecutionPlan
              |
              ↓
        ProviderSelector
              |
              ↓
        PromptBuilder
              |
              ↓
        ProviderManager
        """

        primary_provider, fallback_chain = ProviderSelector.select(
            task=plan.original_task,
            skill_name=plan.skill,
            requested_provider=plan.preferred_provider,
        )

        prompt = PromptBuilder.build(
            plan=plan,
            context=context or {},
        )

        logger.info(
            "LLM Routing | intent=%s | skill=%s | provider=%s | fallback=%s",
            plan.intent,
            plan.skill,
            primary_provider,
            fallback_chain,
        )

        return cls.provider_manager.generate(
            prompt=prompt,
            provider_name=primary_provider,
            fallback_chain=fallback_chain,
            **kwargs,
        )
