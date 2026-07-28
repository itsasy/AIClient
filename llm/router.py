import logging

from llm.intent_analyzer import IntentAnalyzer
from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Enrutador principal de solicitudes al LLM.

    Detecta la skill, ejecuta sus resultados (si existen), construye el prompt,
    selecciona el proveedor y cadena de fallbacks, y genera la respuesta.
    """

    skill_manager = SkillManager()
    provider_manager = ProviderManager()

    @staticmethod
    def detect_skill(query: str):
        """
        Detecta la skill y sus parámetros a partir de la consulta del usuario.
        """
        if not query:
            return None, None
        result = IntentAnalyzer.analyze(query)
        return result.skill_name, result.skill_params

    @classmethod
    def generate(
        cls,
        task: str,
        context=None,
        skill_name=None,
        skill_params=None,
        provider_name: str | None = None,
        **kwargs,
    ) -> str:
        """
        Genera una respuesta LLM para la tarea dada.

        Proceso:
        1. Ejecuta la skill detectada (si existe).
        2. Selecciona el proveedor primario y los fallbacks según la skill.
        3. Construye el prompt con el contexto y el resultado de la skill.
        4. Genera la respuesta con el proveedor seleccionado y su cadena de fallbacks.

        Args:
            task: Tarea o consulta del usuario.
            context: Contexto adicional (proyecto, memoria, etc.).
            skill_name: Nombre de la skill a ejecutar.
            skill_params: Parámetros para la skill.
            provider_name: Proveedor específico (anula selección automática).
            **kwargs: Argumentos adicionales para el proveedor.

        Returns:
            str: Respuesta generada.
        """
        # 1. Ejecutar la skill (si existe)
        skill_result = cls._execute_skill(skill_name, skill_params)

        # 2. Seleccionar proveedor y fallbacks
        primary_provider, fallback_chain = ProviderSelector.select(
            task=task,
            skill_name=skill_name,
            requested_provider=provider_name,
        )

        # 3. Construir el prompt
        prompt = PromptBuilder.build(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_result=skill_result,
        )

        logger.info(
            "Routing | skill=%s | provider=%s | fallbacks=%s | len=%d",
            skill_name or "general",
            primary_provider,
            fallback_chain,
            len(task),
        )

        # 4. Generar respuesta con la cadena de fallbacks
        return cls.provider_manager.generate(
            prompt=prompt,
            provider_name=primary_provider,
            fallback_chain=fallback_chain,
            **kwargs,
        )

    @classmethod
    def _execute_skill(cls, skill_name, skill_params=None):
        """Ejecuta una skill si está definida."""
        if not skill_name:
            return None
        logger.info("Ejecutando skill: %s", skill_name)
        return cls.skill_manager.execute(skill_name, **(skill_params or {}))
