import json
import logging
import os
from agents.base import Agent
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class SelfCriticAgent(Agent):
    name = "self_critic"
    role = "Evaluador y Revisor de Respuestas"

    def __init__(self):
        self.provider_manager = ProviderManager()

    def process(self, task: str, context: dict, draft_response: str) -> dict:
        """
        Evalúa un borrador de respuesta antes de enviarlo al usuario.

        Returns:
            dict: Evaluación estructurada (JSON parseado) o un fallback.
        """
        # Seleccionar un modelo bueno para razonar (ej. Gemini para reflexión)
        provider = ProviderSelector.select(task="critique", skill_name="reflection")

        # Construir el prompt de evaluación (con reglas anti-alucinación)
        prompt = self._build_critique_prompt(task, context, draft_response)

        try:
            raw_eval = self.provider_manager.generate(prompt, provider_name=provider)
            eval_data = self._extract_json(raw_eval)
            logger.info(
                "Self-Critic completado. Score: %s, Riesgo: %s",
                eval_data.get("alignment_score"),
                eval_data.get("hallucination_risk"),
            )
            return eval_data
        except Exception as e:
            logger.exception("Error en Self-Critic. Devolviendo evaluación neutral.")
            return self._fallback_evaluation()

    def _build_critique_prompt(self, task, context, draft_response):
        """Construye el prompt con reglas estrictas anti-alucinación."""

        # Extraer contexto relevante
        context_parts = []
        if context.get("project"):
            context_parts.append(f"PROYECTO:\n{context['project'][:2000]}")
        if context.get("engram"):
            context_parts.append(f"MEMORIA RECUPERADA:\n{context['engram'][:1000]}")
        if context.get("obsidian"):
            context_parts.append(f"OBSIDIAN:\n{context['obsidian'][:1000]}")
        if context.get("spec"):
            context_parts.append(f"SPEC / PLAN:\n{context['spec'][:1000]}")

        context_str = (
            "\n\n".join(context_parts)
            if context_parts
            else "No hay contexto adicional disponible."
        )

        prompt = f"""
Eres un arquitecto de software sénior y revisor crítico. Tu tarea es evaluar el borrador de respuesta que el asistente principal generó para el usuario.

**OBJETIVO ORIGINAL DEL USUARIO:**
{task}

**CONTEXTO DISPONIBLE (LA ÚNICA FUENTE DE VERDAD):**
{context_str}

**BORRADOR DE RESPUESTA A EVALUAR:**
{draft_response}

---

**REGLAS ESTRICTAS (ANTI-ALUCINACIÓN):**
1. **NO** debes introducir información externa que no esté en el CONTEXTO DISPONIBLE.
2. Si el BORRADOR menciona algo que NO está en el CONTEXTO, debes marcarlo como **alto riesgo de alucinación**.
3. Tu veredicto debe basarse ÚNICAMENTE en el CONTEXTO proporcionado.
4. Si el contexto no cubre un punto, el borrador NO debe inventarlo.

**EVALÚA LOS SIGUIENTES PUNTOS:**
- **alignment_score** (0-10): ¿Qué tan bien responde al objetivo original?
- **hallucination_risk** ("low", "medium", "high"): ¿Inventó cosas que no están en el contexto?
- **context_usage** ("excellent", "good", "poor"): ¿Usó correctamente el contexto disponible?
- **coverage**: Descripción de lo que ya está cubierto del objetivo.
- **missing_parts**: Descripción de lo que aún falta para cumplir el objetivo.
- **course_correction_advice**: Consejo concreto para corregir el rumbo si está desviado.
- **summary**: Resumen de la evaluación en 2 líneas para el usuario.

**DEVUELVE SOLO UN JSON VÁLIDO con este formato:**
{{
  "alignment_score": 8,
  "hallucination_risk": "low",
  "context_usage": "excellent",
  "coverage": "Ya cubre la autenticación y el CRUD básico.",
  "missing_parts": "Falta implementar la validación de emails y el rate limiting.",
  "course_correction_advice": "Añadir un middleware de validación antes de guardar en la base de datos.",
  "summary": "✅ Alineado (8/10). Falta la validación de emails."
}}
"""
        return prompt

    def _extract_json(self, text):
        """Extrae el JSON entre llaves del texto."""
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
        raise ValueError("No se encontró JSON válido")

    def _fallback_evaluation(self):
        return {
            "alignment_score": 7,
            "hallucination_risk": "medium",
            "context_usage": "good",
            "coverage": "No se pudo evaluar automáticamente.",
            "missing_parts": "Revisión manual recomendada.",
            "course_correction_advice": "Revisa el código manualmente.",
            "summary": "⚠️ Auto-evaluación no disponible. Revisa manualmente.",
        }
