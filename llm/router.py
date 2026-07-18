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

    Detecta la skill, ejecuta sus resultados (si existen), construye el prompt
    y selecciona el proveedor LLM adecuado.

    Atributos de clase:
        skill_manager (SkillManager): Gestiona la ejecución de skills.
        provider_manager (ProviderManager): Gestiona los proveedores LLM y fallbacks.
    """

    skill_manager = SkillManager()
    provider_manager = ProviderManager()

    @staticmethod
    def detect_skill(query: str):
        """
        Detecta la skill y sus parámetros a partir de la consulta del usuario.

        Args:
            query (str): Consulta del usuario.

        Returns:
            tuple[str, dict]: (skill_name, skill_params) o (None, None).
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
        2. Selecciona el proveedor LLM según la skill y configuración.
        3. Construye el prompt con el contexto y el resultado de la skill.
        4. Genera la respuesta con el proveedor seleccionado.

        Args:
            task (str): Tarea o consulta del usuario.
            context (dict, opcional): Contexto adicional (proyecto, memoria, etc.).
            skill_name (str, opcional): Nombre de la skill a ejecutar.
            skill_params (dict, opcional): Parámetros para la skill.
            provider_name (str, opcional): Proveedor específico (anula selección automática).
            **kwargs: Argumentos adicionales para el proveedor (temperatura, max_tokens, etc.).

        Returns:
            str: Respuesta generada.
        """
        skill_result = cls._execute_skill(skill_name, skill_params)

        selected_provider = ProviderSelector.select(
            task=task,
            skill_name=skill_name,
            requested_provider=provider_name,
        )

        prompt = PromptBuilder.build(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_result=skill_result,
        )

        logger.info(
            "Routing | skill=%s | provider=%s | len=%d",
            skill_name or "general",
            selected_provider,
            len(task),
        )

        return cls.provider_manager.generate(
            prompt=prompt,
            provider_name=selected_provider,
            **kwargs,
        )

    @classmethod
    def _execute_skill(cls, skill_name, skill_params=None):
        """
        Ejecuta una skill si está definida.

        Args:
            skill_name (str, opcional): Nombre de la skill.
            skill_params (dict, opcional): Parámetros para la skill.

        Returns:
            dict: Resultado de la skill, o None si no hay skill.
        """
        if not skill_name:
            return None
        logger.info("Ejecutando skill: %s", skill_name)
        return cls.skill_manager.execute(skill_name, **(skill_params or {}))
