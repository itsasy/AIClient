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

        context = dict(context or {})

        raw_architecture = context.get("architecture")
        if not raw_architecture:
            logger.warning("ArchitectAgent recibió contexto sin architecture.")

        architecture = self._compact_architecture(raw_architecture, max_chars=8000)

        agent_context = {
            "agent_role": {
                "name": self.name,
                "responsibility": (
                    "Analizar la arquitectura real del proyecto "
                    "basándose exclusivamente en la evidencia "
                    "estructural (paths/dirs/summary). "
                    "No inventar módulos ausentes en la lista."
                ),
                "priorities": [
                    "Separación de responsabilidades",
                    "Flujo de ejecución",
                    "Dependencias",
                    "Modularidad",
                    "Mantenibilidad",
                ],
            },
            "analysis_requirements": {
                "must_use_project_evidence": True,
                "must_not_invent_components": True,
                "must_not_assume_microservices": True,
                "must_distinguish_observed_from_inferred": True,
                "language": "es",
                "preferred_layers_if_present": [
                    "core/planning",
                    "core/intent",
                    "runtime",
                    "agents",
                    "skills",
                    "llm",
                    "core/commands",
                    "workflows",
                ],
                "aiclient_flow_hint": (
                    "Si los paths corresponden a AIClient, describe: "
                    "Intent → PlanBuilder/ExecutionPlanner → "
                    "ExecutionEngine → Dispatcher → Agent|Skill → "
                    "(opcional) SelfCritic. "
                    "Menciona TARGET_PROJECT_ROOT vs PROJECT_ROOT solo "
                    "si aparece evidencia o es inferencia explícita."
                ),
            },
            "requested_output": {
                "format": "executive_architecture_analysis",
                "sections": [
                    "Resumen ejecutivo",
                    "Arquitectura actual (capas observadas)",
                    "Flujo principal de ejecución",
                    "Componentes principales (con paths)",
                    "Relaciones y dependencias",
                    "Fortalezas",
                    "Problemas arquitectónicos detectados",
                    "Riesgos",
                    "Recomendaciones prioritarias",
                ],
            },
            "execution": {
                "plan_id": getattr(plan, "id", None),
                "intent": getattr(plan, "intent", None),
                "original_task": getattr(plan, "original_task", ""),
                "step_id": getattr(step, "id", None),
            },
            "project_summary": context.get("project_summary", ""),
            "architecture": architecture,
        }

        if context.get("retry_corrections"):
            agent_context["retry_corrections"] = context["retry_corrections"]
        if context.get("retry_issues"):
            agent_context["retry_issues"] = context["retry_issues"]

        logger.info(
            "ArchitectAgent | architecture=%s | arch_chars=%s | retry_corrections=%s",
            bool(architecture),
            len(architecture) if isinstance(architecture, str) else 0,
            len(context.get("retry_corrections") or []),
        )

        return LLMRouter().generate(
            plan=plan,
            context=agent_context,
        )

    @staticmethod
    def _compact_architecture(architecture: Any, max_chars: int = 8000) -> str:
        if architecture is None:
            return ""
        if isinstance(architecture, dict):
            parts: list[str] = []
            summary = architecture.get("summary") or ""
            if summary:
                parts.append(str(summary)[:2000])
            project = architecture.get("project") or {}
            if project:
                parts.append(
                    f"root={project.get('root_path')} "
                    f"files={project.get('file_count')} "
                    f"dirs={project.get('directory_count')}"
                )
            langs = architecture.get("languages") or {}
            if langs:
                parts.append("languages: " + ", ".join(f"{k}:{v}" for k, v in langs.items()))
            dirs = architecture.get("directories") or []
            if isinstance(dirs, list):
                paths = [(d.get("path") if isinstance(d, dict) else str(d)) for d in dirs[:50]]
                parts.append("dirs:\n" + "\n".join(f"- {p}" for p in paths if p))
            files = architecture.get("files") or []
            if isinstance(files, list):
                fpaths = []
                for f in files[:80]:
                    if isinstance(f, dict):
                        fpaths.append(str(f.get("path") or ""))
                    else:
                        fpaths.append(str(f))
                parts.append("files:\n" + "\n".join(f"- {p}" for p in fpaths if p))
            text = "\n".join(parts)
        else:
            text = str(architecture)
        if len(text) > max_chars:
            return text[:max_chars] + "\n...[truncated]..."
        return text
