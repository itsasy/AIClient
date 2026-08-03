import json
import logging

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Construye el prompt final para proveedores LLM.

    Responsabilidades:

    - Convertir ExecutionPlan en instrucciones.
    - Integrar contexto recuperado.
    - Priorizar conocimiento interno.
    - Mantener contrato estable entre agentes.

    No:

    - Analiza intención.
    - Recupera contexto.
    - Selecciona modelos.
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

        parts = []

        parts.append(
            PromptBuilder._build_system_role(
                plan,
                context,
            )
        )

        identity = PromptBuilder._build_identity(plan)

        if identity:
            parts.append(identity)

        if plan.objective:
            parts.append(f"# OBJECTIVE\n\n{plan.objective}")

        parts.append(f"# USER REQUEST\n\n{plan.original_task}")

        required = PromptBuilder._build_context_requirements(plan)

        if required:
            parts.append(required)

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
            "Prompt construido chars=%s",
            len(prompt),
        )

        return prompt

    # ==========================================================
    # SYSTEM
    # ==========================================================

    @staticmethod
    def _build_system_role(
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        role = context.get(
            "agent_role",
        )

        if role:

            return (
                "Eres AIClient.\n\n"
                "Rol actual:\n"
                f"{json.dumps(role, indent=2, ensure_ascii=False)}\n\n"
                "Actúa siguiendo estrictamente esta responsabilidad."
            )

        if plan.system_role:

            return plan.system_role

        return """
Eres AIClient.

Actúas como ingeniero de software senior.

Especialidades:

- Arquitectura de software
- Clean Architecture
- Domain Driven Design
- Laravel
- NestJS
- Python
- Docker
- DevOps
- Inteligencia Artificial

Reglas:

- Usa primero el contexto proporcionado.
- Respeta estándares internos.
- Respeta Gentleman Skills.
- No inventes información.
- Mantén consistencia con decisiones anteriores.
- Prioriza conocimiento confirmado.
"""

    # ==========================================================
    # IDENTITY
    # ==========================================================

    @staticmethod
    def _build_identity(
        plan: ExecutionPlan,
    ) -> str | None:

        data = {}

        if plan.intent:
            data["intent"] = plan.intent

        if plan.intent_category:
            data["category"] = plan.intent_category

        if plan.agent:
            data["agent"] = plan.agent

        if plan.skills:
            data["skills"] = plan.skills

        if not data:
            return None

        return "# TASK IDENTITY\n\n" + json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

    # ==========================================================
    # CONTEXT REQUIREMENTS
    # ==========================================================

    @staticmethod
    def _build_context_requirements(
        plan: ExecutionPlan,
    ) -> str | None:

        if not plan.context_requirements:
            return None

        return "# REQUIRED CONTEXT\n\n" + "\n".join(
            f"- {item}" for item in plan.context_requirements
        )

    # ==========================================================
    # EXECUTION PLAN
    # ==========================================================

    @staticmethod
    def _build_execution_plan(
        plan: ExecutionPlan,
    ) -> str:

        data = plan.to_dict()

        data.pop(
            "steps",
            None,
        )

        return "# EXECUTION PLAN\n" + json.dumps(
            data,
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

        steps = [
            {
                "description": step.description,
                "skill": step.skill,
                "tool": step.tool,
                "provider": step.provider,
                "params": step.params,
                "expected_output": step.expected_output,
                "retries": step.retries,
                "timeout": step.timeout,
                "status": step.status,
                "metadata": step.metadata,
            }
            for step in plan.steps
        ]

        return "# EXECUTION STEPS\n" + json.dumps(
            steps,
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

        return "# CONSTRAINTS\n\n" + "\n".join(f"- {item}" for item in plan.constraints)

    # ==========================================================
    # CONTEXT
    # ==========================================================

    @staticmethod
    def _build_context(
        context: dict,
    ) -> list[str]:

        sections = []

        titles = {
            "project": "PROJECT CONTEXT",
            "memory": "CONVERSATION MEMORY",
            "documents": "DOCUMENTS",
            "obsidian": "OBSIDIAN KNOWLEDGE",
            "spec": "SPECIFICATION",
            "standards": "PROJECT STANDARDS",
            "gentleman": "GENTLEMAN SKILLS",
        }

        handled = set(titles.keys())

        for key, title in titles.items():

            value = context.get(key)

            if not value:
                continue

            if key == "gentleman":

                sections.append(PromptBuilder._build_gentleman_context(value))

                continue

            sections.append(f"#{title}\n\n" f"{PromptBuilder._format_value(value)}")

        handled.add("engram")

        engram = context.get("engram")

        if isinstance(engram, dict):

            if engram.get("memory"):

                sections.append(
                    "# ENGRAM MEMORY\n\n" + PromptBuilder._format_value(engram["memory"])
                )

            if engram.get("skills"):

                sections.append(
                    "# ENGRAM SKILLS\n\n" + PromptBuilder._format_value(engram["skills"])
                )

        for key, value in context.items():

            if key in handled:
                continue

            if not value:
                continue

            sections.append(f"#{key.upper()}\n\n" + PromptBuilder._format_value(value))

        return sections

    # ==========================================================
    # GENTLEMAN
    # ==========================================================

    @staticmethod
    def _build_gentleman_context(
        value: dict,
    ) -> str:

        skills = {}

        for name, data in value.items():

            if isinstance(data, dict):

                skills[name] = data.get(
                    "content",
                    "",
                )

            else:

                skills[name] = data

        return (
            "# GENTLEMAN SKILLS\n\n"
            + PromptBuilder._format_value(skills)
            + "\n\nEstas instrucciones tienen "
            "prioridad sobre conocimiento general."
        )

    # ==========================================================
    # SETTINGS
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
