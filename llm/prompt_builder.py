import json
import logging

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Constructor central de prompts.

    Responsabilidades:

    - Transformar ExecutionPlan en instrucciones LLM.
    - Integrar contexto externo (Engram, Obsidian, proyecto, Gentleman Skills).
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

        # Log para depuración
        logger.info(f"📦 Contexto recibido en PromptBuilder: {list(context.keys())}")

        sections = []

        # --------------------------------------------------
        # 1. SYSTEM ROLE
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
        # 2. GENTLEMAN SKILLS (prioridad máxima)
        # --------------------------------------------------
        if "gentleman_skills" in context:
            sections.append(f"""
# ⚠️ ATENCIÓN: DEBES SEGUIR ESTAS INSTRUCCIONES OBLIGATORIAMENTE

{context.pop('gentleman_skills')}

**REGLAS ESTRICTAS:**
- **NO** generes código que no siga estas prácticas.
- **NO** uses patrones antiguos o desactualizados.
- **SIEMPRE** prioriza lo que dice la skill por encima de tu conocimiento general.
- Si la skill menciona una versión específica de un framework, usa ESA versión.
""")

        # --------------------------------------------------
        # 3. EXECUTION PLAN
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
        # 4. USER TASK
        # --------------------------------------------------

        sections.append(f"""
## Tarea original del usuario

{plan.original_task}
""")

        # --------------------------------------------------
        # 5. CONTEXTO DEL SISTEMA (resto)
        # --------------------------------------------------

        if context:
            sections.append("## Contexto disponible\n" + PromptBuilder._serialize_context(context))

        # --------------------------------------------------
        # 6. INSTRUCCIONES SEGÚN MODO
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
        - estándares
        - (gentleman_skills ya se ha extraído)
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
