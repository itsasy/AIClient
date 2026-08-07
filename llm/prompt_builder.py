import json
import logging

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Construye el prompt final para proveedores LLM.

    Usa ExecutionPlan + Context (ya construido).

    No busca contexto ni selecciona proveedores.
    """

    @staticmethod
    def build(plan: ExecutionPlan, context: dict | None = None) -> str:
        context = context or {}

        logger.info("Construyendo prompt | context=%s", list(context.keys()))

        parts = []

        # 1. System role
        parts.append(PromptBuilder._build_system_role(plan, context))

        # 2. Identity (usando nuevo modelo)
        identity = PromptBuilder._build_identity(plan)
        if identity:
            parts.append(identity)

        # 3. Objective
        if plan.objective:
            parts.append(f"# OBJECTIVE\n\n{plan.objective}")

        # 4. User request
        parts.append(f"# USER REQUEST\n\n{plan.original_task}")

        # 5. Required context
        required = PromptBuilder._build_context_requirements(plan)
        if required:
            parts.append(required)

        # 6. Constraints
        constraints = PromptBuilder._build_constraints(plan)
        if constraints:
            parts.append(constraints)

        # 7. Execution plan (sin pasos, la info va abajo)
        parts.append(PromptBuilder._build_execution_plan(plan))

        # 8. Steps
        steps = PromptBuilder._build_steps(plan)
        if steps:
            parts.append(steps)

        # 9. Context
        parts.extend(PromptBuilder._build_context(context))

        # 10. Settings
        settings = PromptBuilder._build_llm_settings(plan)
        if settings:
            parts.append(settings)

        # 11. Execution mode
        parts.append(PromptBuilder._build_execution_mode(plan))

        prompt = "\n\n".join(parts)

        logger.info("Prompt construido chars=%s", len(prompt))
        return prompt

    # ==========================================================
    # System role
    # ==========================================================

    @staticmethod
    def _build_system_role(plan: ExecutionPlan, context: dict) -> str:
        role = context.get("agent_role")

        if role:
            return (
                "Eres AIClient.\n\n"
                "Rol actual:\n"
                f"{json.dumps(role, indent=2, ensure_ascii=False)}\n\n"
                "Actúa siguiendo estrictamente esta responsabilidad."
            )

        if plan.metadata.get("system_role"):
            return plan.metadata["system_role"]

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
    # Identity (nuevo modelo)
    # ==========================================================

    @staticmethod
    def _build_identity(plan: ExecutionPlan) -> str | None:
        data = {}

        if plan.intent:
            data["intent"] = plan.intent
        if plan.intent_category:
            data["category"] = plan.intent_category
        if plan.execution_unit_type:
            data["unit_type"] = plan.execution_unit_type
        if plan.execution_unit:
            data["unit_name"] = plan.execution_unit
        if plan.steps:
            data["steps_count"] = len(plan.steps)

        if not data:
            return None

        return "# TASK IDENTITY\n\n" + json.dumps(data, indent=2, ensure_ascii=False)

    # ==========================================================
    # Context requirements
    # ==========================================================

    @staticmethod
    def _build_context_requirements(plan: ExecutionPlan) -> str | None:
        if not plan.context_requirements:
            return None
        return "# REQUIRED CONTEXT\n\n" + "\n".join(
            f"- {item}" for item in plan.context_requirements
        )

    # ==========================================================
    # Constraints
    # ==========================================================

    @staticmethod
    def _build_constraints(plan: ExecutionPlan) -> str | None:
        if not plan.constraints:
            return None
        return "# CONSTRAINTS\n\n" + "\n".join(f"- {item}" for item in plan.constraints)

    # ==========================================================
    # Execution plan
    # ==========================================================

    @staticmethod
    def _build_execution_plan(plan: ExecutionPlan) -> str:
        data = plan.to_dict()
        data.pop("steps", None)  # se añaden aparte
        return "# EXECUTION PLAN\n" + json.dumps(data, indent=2, ensure_ascii=False)

    # ==========================================================
    # Steps (nuevo modelo)
    # ==========================================================

    @staticmethod
    def _build_steps(plan: ExecutionPlan) -> str | None:
        if not plan.steps:
            return None

        steps = [
            {
                "description": step.description,
                "unit_type": step.unit_type,
                "unit_name": step.unit_name,
                "params": step.params,
                "expected_output": step.expected_output,
                "retries": step.retries,
                "timeout": step.timeout,
                "status": step.status,
                "metadata": step.metadata,
            }
            for step in plan.steps
        ]

        return "# EXECUTION STEPS\n" + json.dumps(steps, indent=2, ensure_ascii=False)

    # ==========================================================
    # LLM settings
    # ==========================================================

    @staticmethod
    def _build_llm_settings(plan: ExecutionPlan) -> str | None:
        values = []

        # Provider puede estar en metadata
        if plan.metadata.get("preferred_provider"):
            values.append(f"Provider: {plan.metadata['preferred_provider']}")

        if plan.metadata.get("temperature") is not None:
            values.append(f"Temperature: {plan.metadata['temperature']}")

        if plan.metadata.get("max_tokens") is not None:
            values.append(f"Max Tokens: {plan.metadata['max_tokens']}")

        if not values:
            return None

        return "# LLM SETTINGS\n\n" + "\n".join(values)

    # ==========================================================
    # Execution mode
    # ==========================================================

    @staticmethod
    def _build_execution_mode(plan: ExecutionPlan) -> str:
        return "# EXECUTION MODE\n\n" + plan.execution_mode

    # ==========================================================
    # Context
    # ==========================================================

    @staticmethod
    def _build_context(context: dict) -> list[str]:
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
            sections.append(f"#{title}\n\n" + PromptBuilder._format_value(value))

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
    # Gentleman context
    # ==========================================================

    @staticmethod
    def _build_gentleman_context(value: dict) -> str:
        skills = {}
        for name, data in value.items():
            if isinstance(data, dict):
                skills[name] = data.get("content", "")
            else:
                skills[name] = data
        return (
            "# GENTLEMAN SKILLS\n\n"
            + PromptBuilder._format_value(skills)
            + "\n\nEstas instrucciones tienen prioridad sobre conocimiento general."
        )

    # ==========================================================
    # Format
    # ==========================================================

    @staticmethod
    def _format_value(value):
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except Exception:
            return str(value)
