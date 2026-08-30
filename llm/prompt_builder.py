from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


from llm.prompt_type import PromptType
from llm.prompt_mixins.sanitization_mixin import PromptSanitizationMixin
from llm.prompt_mixins.composition_mixin import PromptCompositionMixin

class PromptBuilder(
    PromptSanitizationMixin,
    PromptCompositionMixin,
):
    """
    Construye prompts deterministas para proveedores LLM.

    Responsabilidades:
        - Convertir ExecutionPlan + contexto en un prompt.
        - Normalizar, priorizar y limitar el contexto.
        - Separar instrucciones, tarea, plan y evidencia.
        - Preservar hechos vs inferencias.
        - Modo lean para generación de código / landings.

    No:
        - Selecciona proveedores.
        - Ejecuta herramientas.
        - Decide planificación.
        - Ejecuta Agents o Skills.
        - Modifica el ExecutionPlan.
    """

    MAX_CONTEXT_CHARS = 30_000

    # Presupuesto por clave (chars serializados) en modo normal.
    # En lean se aplican límites más estrictos.
    KEY_BUDGETS: dict[str, int] = {
        "architecture": 12_000,
        "project_analysis": 2_000,
        "project_summary": 1_500,
        "standards": 6_000,
        "engram": 3_000,
        "obsidian": 3_000,
        "gentleman": 2_000,
        "swarmforge": 2_000,
        "execution": 2_500,
        "dependency_text": 4_000,
        "code_artifacts": 2_000,
        "coding_task": 4_000,
        "requested_output": 2_000,
        "requested_paths": 500,
        "locale": 800,
        "locale_summary": 1_200,
        "template": 8_000,
    }

    LEAN_KEY_BUDGETS: dict[str, int] = {
        "architecture": 4_000,
        "project_analysis": 800,
        "project_summary": 800,
        "standards": 4_000,
        "engram": 1_500,
        "execution": 800,
        "dependency_text": 3_000,
        "coding_task": 4_000,
        "requested_output": 2_000,
        "requested_paths": 400,
        "locale_summary": 800,
        "template": 5_000,
    }

    # Claves que nunca deben entrar al prompt (ruido / tamaño).
    DROP_KEYS = frozenset(
        {
            "snapshot",
            "architecture_context",  # se normaliza a "architecture"
            "project",  # provider crudo; usar project_summary / architecture
            "loaded_context",
            "memory",
            "conversation_history",  # multi_turn lo maneja aparte si aplica
        }
    )

    SYSTEM_INSTRUCTIONS = """
Eres un ingeniero de software senior y arquitecto de sistemas.

Tu respuesta debe basarse únicamente en la evidencia proporcionada
por la tarea, el ExecutionPlan y el contexto disponible.

Reglas obligatorias:

1. No inventes componentes, archivos, tecnologías, servicios ni capacidades.
2. No afirmes como hecho aquello que solo puede inferirse.
3. Diferencia explícitamente entre:
   - hechos observados;
   - inferencias razonables;
   - información desconocida.
4. No confundas una estructura de carpetas con un límite arquitectónico.
5. No describas un sistema como microservicios sin evidencia explícita.
6. No inventes infraestructura, bases de datos, colas, APIs o comunicaciones
   que no estén presentes en la evidencia.
7. Si la información disponible es insuficiente, indícalo claramente.
8. Prioriza la implementación y evidencia real sobre descripciones genéricas.
9. Respeta las restricciones y requisitos incluidos en el contexto
   (standards, estilo de código, design system, contratos de pagos).
10. No inventes stack (framework, ORM, librería UI) no pedido en la tarea.
11. Operaciones de cobro/facturación: respeta contratos e idempotencia si aplican.
12. Responde en español salvo que la tarea solicite explícitamente otro idioma.
""".strip()

    CRITIQUE_INSTRUCTIONS = """
## Modo de evaluación

Debes evaluar el resultado de la ejecución respecto de la tarea,
el ExecutionPlan y la evidencia disponible.

Determina:

1. si la tarea fue completada correctamente;
2. qué problemas concretos existen;
3. qué correcciones serían necesarias;
4. una puntuación de 0 a 10;
5. una justificación breve.

Debes devolver EXCLUSIVAMENTE un objeto JSON válido.

El JSON debe tener exactamente esta estructura:

{
  "pass": true,
  "score": 10,
  "issues": [],
  "corrections": [],
  "reason": "Explicación breve."
}

Reglas:

- "pass" debe ser booleano.
- "score" debe ser un entero entre 0 y 10.
- "issues" debe ser una lista de strings.
- "corrections" debe ser una lista de strings.
- "reason" debe ser un string.
- No incluyas Markdown.
- No incluyas bloques ```json.
- No incluyas texto antes ni después del JSON.
- No inventes errores que no puedan justificarse con la evidencia.
- Si la evidencia no permite determinar algo, indícalo en "reason".
""".strip()

    # Orden de inclusión (prioridad alta → baja).
    CONTEXT_PRIORITY = (
        "agent_role",
        "coding_task",
        "requested_output",
        "requested_paths",
        "analysis_requirements",
        "template",
        "standards",
        "locale_summary",
        "locale",
        "project_summary",
        "architecture",
        "project_analysis",
        "dependency_text",
        "code_artifacts",
        "gentleman",
        "swarmforge",
        "engram",
        "obsidian",
        "retry_issues",
        "retry_corrections",
        "execution",
        "additional_instructions",
        "lean_prompt",
    )

    SPECIALIZED_CONTEXT_KEYS = frozenset(
        {
            "agent_role",
            "analysis_requirements",
            "requested_output",
            "requested_paths",
            "coding_task",
            "retry_issues",
            "retry_corrections",
            "execution",
            "lean_prompt",
            "additional_instructions",
        }
    )

    def __init__(
        self,
        max_context_chars: int | None = None,
    ) -> None:
        self.max_context_chars = (
            max_context_chars if max_context_chars is not None else self.MAX_CONTEXT_CHARS
        )
        if self.max_context_chars <= 0:
            raise ValueError("max_context_chars debe ser mayor que cero.")

    def build(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
        prompt_type: PromptType = PromptType.DEFAULT,
    ) -> str:
        if plan is None:
            raise ValueError("plan no puede ser None.")

        if not isinstance(prompt_type, PromptType):
            try:
                prompt_type = PromptType(prompt_type)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"prompt_type inválido: {prompt_type!r}") from exc

        raw_context = dict(context or {})
        lean = self._is_lean(plan, raw_context)

        logger.info(
            "Construyendo prompt | plan=%s | type=%s | lean=%s | context=%s",
            plan.id,
            prompt_type.value,
            lean,
            list(raw_context.keys()),
        )

        prepared_context = self._prepare_context(raw_context, lean=lean)

        sizes = {
            k: len(self._serialize(v)) if not isinstance(v, str) else len(v)
            for k, v in prepared_context.items()
        }
        logger.info(
            "PromptBuilder | prepared_context_chars=%s | total=%s",
            sizes,
            sum(sizes.values()),
        )

        prompt = self._compose(
            plan=plan,
            context=prepared_context,
            prompt_type=prompt_type,
            lean=lean,
        )

        if len(prompt) > self.max_context_chars:
            logger.warning(
                "Prompt excede límite | chars=%s | max=%s",
                len(prompt),
                self.max_context_chars,
            )
            prompt = self._truncate_prompt(prompt)

        logger.info(
            "Prompt construido | plan=%s | type=%s | chars=%s",
            plan.id,
            prompt_type.value,
            len(prompt),
        )
        return prompt

