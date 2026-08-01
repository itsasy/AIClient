import json
import logging

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Constructor central de prompts.

    Responsabilidades:

    - Transformar ExecutionPlan en instrucciones LLM.
    - Integrar contexto externo.
    - Mantener separación entre planificación y generación.

    No:
    - Detecta intención.
    - Ejecuta skills.
    - Consulta memoria directamente.
    """

    @staticmethod
    def build(
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        sections = []

        # --------------------------------------------------
        # SYSTEM ROLE
        # --------------------------------------------------

        sections.append("""
Eres un asistente de ingeniería de software avanzado.

Tu objetivo es resolver la tarea siguiendo el ExecutionPlan proporcionado.

Reglas:
- Respeta las restricciones.
- Usa el contexto disponible.
- No inventes información inexistente.
- Si falta información crítica, indícalo.
- Prioriza soluciones mantenibles y escalables.
""")

        # --------------------------------------------------
        # EXECUTION PLAN
        # --------------------------------------------------

        sections.append(
            "## Execution Plan\n"
            + json.dumps(
                plan.to_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )

        # --------------------------------------------------
        # USER TASK
        # --------------------------------------------------

        sections.append(f"""
## Tarea original del usuario

{plan.original_task}
""")

        # --------------------------------------------------
        # CONTEXTO DEL SISTEMA
        # --------------------------------------------------

        if context:

            sections.append("## Contexto disponible\n" + PromptBuilder._serialize_context(context))

        # --------------------------------------------------
        # INSTRUCCIONES SEGÚN MODO
        # --------------------------------------------------

        if plan.execution_mode == "multi_step":

            sections.append("""
Modo de ejecución:
MULTI PASO

Analiza cada paso del plan antes de responder.
Mantén consistencia entre las etapas.
""")

        else:

            sections.append("""
Modo de ejecución:
TAREA ÚNICA

Entrega directamente la solución solicitada.
""")

        prompt = "\n\n".join(sections)

        logger.debug(
            "Prompt generado | chars=%d",
            len(prompt),
        )

        return prompt

    @staticmethod
    def _serialize_context(
        context: dict,
    ) -> str:
        """
        Serializa contexto externo.

        Preparado para:
        - Engram
        - Obsidian
        - documentos
        - proyecto
        - memoria conversacional
        """

        output = []

        for key, value in context.items():

            output.append(f"""
### {key}

{PromptBuilder._format_value(value)}
""")

        return "\n".join(output)

    @staticmethod
    def _format_value(value):

        if isinstance(value, str):
            return value

        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
            )

        except Exception:

            return str(value)
