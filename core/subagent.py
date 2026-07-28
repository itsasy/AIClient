import logging
from skills.manager import SkillManager
from agents.self_critic import SelfCriticAgent
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class Subagent:
    """
    Subagente para ejecutar un paso de un plan.
    - Ejecuta la skill solicitada.
    - Evalúa el resultado con SelfCritic.
    - Si la puntuación es baja, aplica la corrección sugerida y reintenta.
    - Máximo de reintentos configurable.
    """

    def __init__(self):
        self.skill_manager = SkillManager()
        self.critic = SelfCriticAgent()
        self.provider_manager = ProviderManager()

    def execute_with_retry(
        self,
        step_description: str,
        skill_name: str,
        params: dict,
        context: dict = None,
        max_retries: int = 2,
    ) -> tuple[dict, dict]:
        """
        Ejecuta un paso con reintentos y auto-corrección.

        Args:
            step_description: Descripción del paso (se usa para el crítico).
            skill_name: Nombre de la skill a ejecutar.
            params: Parámetros para la skill.
            context: Contexto del orquestador (se pasa al crítico).
            max_retries: Número máximo de reintentos.

        Returns:
            tuple[dict, dict]: (resultado_de_la_skill, evaluación_del_crítico)
        """
        retry_count = 0
        last_result = None
        last_eval = None

        while retry_count <= max_retries:
            try:
                # 1. Ejecutar la skill
                logger.info(
                    "Subagente ejecutando '%s' (intento %d/%d)",
                    step_description,
                    retry_count + 1,
                    max_retries + 1,
                )
                result = self.skill_manager.execute(skill_name, **params)
                output = self._extract_output(result)

                # 2. Evaluar con SelfCritic
                eval_result = self.critic.process(
                    task=step_description, context=context or {}, draft_response=output
                )
                last_eval = eval_result

                # 3. Verificar si el paso es aceptable
                alignment = eval_result.get("alignment_score", 0)
                if alignment >= 5:
                    logger.info(
                        "✅ Paso '%s' validado (Score: %d)", step_description, alignment
                    )
                    return result, eval_result

                # 4. Si no pasa, aplicar corrección (si hay sugerencia)
                logger.warning(
                    "⚠️ Paso '%s' desviado (Score: %d). Reintentando...",
                    step_description,
                    alignment,
                )
                advice = eval_result.get("course_correction_advice", "")
                if advice:
                    params = self._apply_correction(params, advice, step_description)
                else:
                    logger.warning(
                        "No hay consejo de corrección. Reintentando sin cambios."
                    )

                retry_count += 1

            except Exception as e:
                logger.exception(
                    "❌ Error en subagente para '%s'. Reintento %d/%d",
                    step_description,
                    retry_count + 1,
                    max_retries + 1,
                )
                retry_count += 1
                if retry_count > max_retries:
                    raise

        # Si se agotan los reintentos, devolver el último resultado y evaluación
        logger.warning(
            "⚠️ Se agotaron los reintentos para '%s'. Devolviendo último resultado.",
            step_description,
        )
        return last_result, last_eval

    def _extract_output(self, result: dict) -> str:
        """Extrae la salida legible de un resultado de skill."""
        if isinstance(result, dict):
            payload = result.get("payload", {})
            return payload.get("output") or payload.get("message") or str(result)
        return str(result)

    def _apply_correction(self, params: dict, advice: str, step_desc: str) -> dict:
        """
        Aplica el consejo de corrección a los parámetros de la skill.
        Modifica el campo 'task', 'code_snippet' o 'command' según corresponda.
        """
        new_params = dict(params)  # Copia para no mutar el original

        if "task" in new_params:
            new_params["task"] = (
                new_params["task"]
                + f"\n\n[REINTENTO] Consejo de corrección del crítico: {advice}"
            )
            logger.debug("Corrección aplicada al campo 'task'.")
        elif "code_snippet" in new_params:
            new_params["code_snippet"] = (
                new_params["code_snippet"]
                + f"\n# [REINTENTO] Corrección sugerida: {advice}"
            )
            logger.debug("Corrección aplicada al campo 'code_snippet'.")
        elif "command" in new_params:
            # Para shell, no podemos modificar el comando directamente sin riesgo.
            # En su lugar, añadimos un comentario en la descripción (si existe).
            logger.debug(
                "No se puede modificar 'command' directamente. Se omite corrección."
            )
        else:
            logger.debug("No se encontró campo modificable. Se omite corrección.")

        return new_params
