import json
import logging

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Construye el prompt final para cualquier proveedor LLM.

    Responsabilidades:

    - Convertir ExecutionPlan en instrucciones LLM.
    - Integrar contexto recuperado.
    - Mantener estructura consistente para todos los agentes.

    No:

    - Analiza intención.
    - Consulta memoria.
    - Selecciona proveedores.
    """

    @staticmethod
    def build(
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        logger.info(
            "Construyendo prompt | context=%s",
            list(context.keys()),
        )

        parts: list[str] = []

        parts.append(PromptBuilder._build_system_role(plan))

        agent_role = context.get("agent_role")

        if agent_role:

            parts.append(
                "# AGENT ROLE\n\n"
                f"{PromptBuilder._format_value(agent_role)}\n\n"
                "Debes actuar siguiendo este rol."
            )

        if plan.objective:

            parts.append(f"# OBJECTIVE\n\n{plan.objective}")

        parts.append(f"# USER REQUEST\n\n{plan.original_task}")

        constraints = PromptBuilder._build_constraints(plan)

        if constraints:
            parts.append(constraints)

        parts.append(PromptBuilder._build_execution_plan(plan))

        steps = PromptBuilder._build_steps(plan)

        if steps:
            parts.append(steps)

        parts.extend(PromptBuilder._build_context(context))

        settings = PromptBuilder._build_llm_settings(plan)

        if settings:
            parts.append(settings)

        parts.append(PromptBuilder._build_execution_mode(plan))

        prompt = "\n\n".join(parts)

        logger.info(
            "Prompt construido (%d caracteres)",
            len(prompt),
        )

        return prompt

    # ==========================================================
    # SYSTEM
    # ==========================================================

    @staticmethod
    def _build_system_role(
        plan: ExecutionPlan,
    ) -> str:

        if plan.system_role:
            return plan.system_role

        return """
Eres AIClient.

Eres un ingeniero de software senior especializado en:

- Arquitectura
- Clean Architecture
- Domain Driven Design (DDD)
- Laravel
- NestJS
- Python
- Docker
- DevOps
- Inteligencia Artificial

Objetivo:

Resolver la tarea utilizando TODO el contexto disponible.

Reglas:

- Nunca ignores Gentleman Skills.
- Nunca inventes información.
- Prioriza el contexto antes que conocimiento general.
- Mantén consistencia entre respuestas.
- Reutiliza conocimiento previo cuando exista.
- Usa Engram, Obsidian y documentos cuando estén disponibles.
"""

    # ==========================================================
    # EXECUTION PLAN
    # ==========================================================

    @staticmethod
    def _build_execution_plan(
        plan: ExecutionPlan,
    ) -> str:

        plan_dict = plan.to_dict()

        plan_dict.pop(
            "steps",
            None,
        )

        return "# EXECUTION PLAN\n" + json.dumps(
            plan_dict,
            indent=2,
            ensure_ascii=False,
        )

    # ==========================================================
    # STEPS
    # ==========================================================

    @staticmethod
    def _build_steps(
        plan: ExecutionPlan,
    ) -> str | None:

        if not plan.steps:
            return None

        return "# EXECUTION STEPS\n" + json.dumps(
            [
                {
                    "description": step.description,
                    "skill": step.skill,
                    "tool": step.tool,
                    "provider": step.provider,
                    "params": step.params,
                    "status": step.status,
                }
                for step in plan.steps
            ],
            indent=2,
            ensure_ascii=False,
        )

    # ==========================================================
    # CONSTRAINTS
    # ==========================================================

    @staticmethod
    def _build_constraints(
        plan: ExecutionPlan,
    ) -> str | None:

        if not plan.constraints:
            return None

        return "# CONSTRAINTS\n\n" + "\n".join(f"- {constraint}" for constraint in plan.constraints)

    # ==========================================================
    # CONTEXT
    # ==========================================================

    @staticmethod
    def _build_context(
        context: dict,
    ) -> list[str]:

        sections: list[str] = []

        titles = {
            "project": "PROJECT CONTEXT",
            "memory": "CONVERSATION MEMORY",
            "obsidian": "OBSIDIAN KNOWLEDGE",
            "documents": "RELATED DOCUMENTS",
            "spec": "SPECIFICATION",
            "standards": "PROJECT STANDARDS",
            "gentleman": "GENTLEMAN SKILLS",
        }

        for key, title in titles.items():

            value = context.get(key)

            if not value:
                continue

            block = f"# {title}\n\n" f"{PromptBuilder._format_value(value)}"

            if key == "gentleman":

                block += "\n\nEstas instrucciones tienen prioridad " "sobre conocimiento general."

            sections.append(block)

        # Engram separado en memoria y skills

        engram = context.get("engram")

        if isinstance(engram, dict):

            memory = engram.get("memory")

            if memory:

                sections.append("# ENGRAM MEMORY\n\n" f"{PromptBuilder._format_value(memory)}")

            skills = engram.get("skills")

            if skills:

                sections.append("# ENGRAM SKILLS\n\n" f"{PromptBuilder._format_value(skills)}")

        return sections

    # ==========================================================
    # LLM SETTINGS
    # ==========================================================

    @staticmethod
    def _build_llm_settings(
        plan: ExecutionPlan,
    ) -> str | None:

        values = []

        if plan.preferred_provider:
            values.append(f"Provider: {plan.preferred_provider}")

        if plan.temperature is not None:
            values.append(f"Temperature: {plan.temperature}")

        if plan.max_tokens is not None:
            values.append(f"Max Tokens: {plan.max_tokens}")

        if not values:
            return None

        return "# LLM SETTINGS\n\n" + "\n".join(values)

    # ==========================================================
    # EXECUTION MODE
    # ==========================================================

    @staticmethod
    def _build_execution_mode(
        plan: ExecutionPlan,
    ) -> str:

        return "# EXECUTION MODE\n\n" f"{plan.execution_mode}"

    # ==========================================================
    # FORMAT
    # ==========================================================

    @staticmethod
    def _format_value(
        value,
    ):

        if isinstance(value, str):
            return value

        try:

            return json.dumps(
                value,
                indent=2,
                ensure_ascii=False,
            )

        except Exception:

            return str(value)
