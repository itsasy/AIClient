from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class ArchitectAgent(Agent):
    """
    Analiza la arquitectura de un proyecto.

    Responsabilidad:

        Project architecture
            ↓
        architectural reasoning
            ↓
        executive analysis

    No inspecciona directamente el filesystem.
    El proyecto debe llegar mediante el contexto producido
    por analyze_project.
    """

    name = "architect"

    description = (
        "Analiza arquitecturas de software y genera " "evaluaciones arquitectónicas ejecutivas."
    )

    version = "2.0"

    aliases = (
        "architecture",
        "software_architect",
    )

    capabilities = (
        "architecture_analysis",
        "project_analysis",
        "architecture_review",
    )

    role = "Arquitecto de Software"

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = dict(
            context or {},
        )

        architecture = context.get(
            "architecture",
        )

        if not architecture:
            logger.warning(
                "ArchitectAgent recibió contexto " "sin architecture.",
            )

        agent_context = {
            "agent_role": {
                "name": self.name,
                "responsibility": (
                    "Analizar la arquitectura real del proyecto "
                    "basándose exclusivamente en la evidencia "
                    "proporcionada por el contexto."
                ),
                "priorities": [
                    "Separación de responsabilidades",
                    "Flujo de ejecución",
                    "Dependencias",
                    "Modularidad",
                    "Mantenibilidad",
                    "Escalabilidad",
                    "Seguridad",
                    "Testabilidad",
                ],
            },
            "analysis_requirements": {
                "must_use_project_evidence": True,
                "must_not_invent_components": True,
                "must_not_assume_microservices": True,
                "must_distinguish_observed_from_inferred": True,
                "language": "es",
            },
            "requested_output": {
                "format": "executive_architecture_analysis",
                "sections": [
                    "Resumen ejecutivo",
                    "Arquitectura actual",
                    "Flujo principal de ejecución",
                    "Componentes principales",
                    "Relaciones y dependencias",
                    "Fortalezas",
                    "Problemas arquitectónicos detectados",
                    "Riesgos",
                    "Recomendaciones prioritarias",
                ],
            },
            "execution": {
                "plan_id": getattr(
                    plan,
                    "id",
                    None,
                ),
                "intent": getattr(
                    plan,
                    "intent",
                    None,
                ),
                "original_task": getattr(
                    plan,
                    "original_task",
                    "",
                ),
                "step_id": getattr(
                    step,
                    "id",
                    None,
                ),
            },
            "project_summary": context.get(
                "project_summary",
                "",
            ),
            "architecture": architecture or {},
        }

        if context.get("retry_corrections"):
            agent_context["retry_corrections"] = context["retry_corrections"]

        if context.get("retry_issues"):
            agent_context["retry_issues"] = context["retry_issues"]

        logger.info(
            "ArchitectAgent | architecture=%s | retry_corrections=%s | retry_issues=%s",
            bool(architecture),
            len(context.get("retry_corrections") or []),
            len(context.get("retry_issues") or []),
        )

        return LLMRouter().generate(
            plan=plan,
            context=agent_context,
        )
