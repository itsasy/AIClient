from __future__ import annotations

import re
from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class SpecWorkflow(BaseWorkflow):
    """
    /spec <descripción>

    Genera una especificación formal y la persiste en disco.

    Flujo:
        task_agent (razona → texto/JSON de spec)
            ↓ depends_on
        write_file (actúa; content materializado o generado en el step)
    """

    name = "spec"
    description = "Genera una especificación formal para una tarea."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        topic = (arguments or "").strip()
        safe_name = self._sanitize_name(topic) or "spec"
        spec_path = f".specs/{safe_name}.md"

        plan = ExecutionPlan(
            original_task=f"/spec {topic}",
            intent="spec",
            intent_category="planning",
            objective=f"Crear especificación formal: {topic}",
            execution_mode="multi_step",
        )

        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True
        plan.context_requirements["project"] = False
        plan.governance["allow_write"] = True

        plan.params["topic"] = topic
        plan.params["spec_path"] = spec_path

        generate = plan.add_step(
            description=f"Generar especificación para: {topic}",
            unit_type="agent",
            unit_name="task_agent",
            params={
                "task": (
                    f"Redacta una especificación técnica clara y completa para: {topic}.\n\n"
                    "Incluye:\n"
                    "1. Objetivo\n"
                    "2. Alcance (in / out)\n"
                    "3. Requisitos funcionales\n"
                    "4. Requisitos no funcionales\n"
                    "5. Criterios de aceptación\n"
                    "6. Riesgos y supuestos\n\n"
                    "Responde SOLO con el documento en Markdown, sin preámbulos."
                ),
                "mode": "spec",
                "path": spec_path,
            },
            expected_output="Especificación en Markdown.",
            metadata={
                "stage": "spec_generation",
                "produces": "code_artifact",
            },
        )

        write = plan.add_step(
            description=f"Guardar especificación en {spec_path}",
            unit_type="skill",
            unit_name="write_file",
            params={
                "path": spec_path,
            },
            expected_output="Archivo de especificación creado.",
            metadata={
                "stage": "materialization",
                "consumes": "code_artifact",
            },
        )
        write.depends_on.append(generate.id)

        plan.metadata["requires_self_critic"] = False
        plan.metadata["workflow"] = "spec"

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        if not arguments or not arguments.strip():
            return False, "Se requiere una descripción para /spec"
        return True, ""

    def _sanitize_name(self, name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]+", "_", name[:60]).strip("_")
        return cleaned.lower()
