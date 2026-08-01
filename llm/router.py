import logging

from llm.intent_analyzer import IntentAnalyzer
from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Enrutador principal de solicitudes al LLM.

    Detecta la skill, ejecuta sus resultados (si existen), construye el prompt,
    selecciona el proveedor y cadena de fallbacks, y genera la respuesta.
    """

    provider_manager = ProviderManager()

    @classmethod
    def generate(
        plan: ExecutionPlan,
        context=None,
    ) -> str:
        prompt = PromptBuilder.build(
            task=plan.task,
            context=context,
            skill_name=plan.skill_name,
        )
