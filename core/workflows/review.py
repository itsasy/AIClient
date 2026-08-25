from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan
from core.locale.detect import detect_locale

try:
    from core.locale.resolver import resolve_locale
except ImportError:

    def resolve_locale(code: str | None, engram: Any | None = None) -> dict[str, Any]:
        return {
            "locale_code": code,
            "locale_summary": "",
            "sources": ["default"],
        }


REVIEW_STANDARDS_INSTRUCTIONS = """
Al revisar:
1. Contrastá la estructura real con Standards/Arquitectura-de-proyecto
   (domain vs adapters vs ui; sin SDKs de un solo país en el core).
2. Pagos/fisco: ¿hay contratos PaymentProvider / ElectronicInvoiceProvider
   o cobros duplicados en vistas/servicios?
3. Estilo: ¿naming y control de flujo coherentes?
   (Standards/Estilo-de-codigo; no mezclar paradigmas sin motivo).
4. UI: si hay src/ui, ¿un design system o estilos contradictorios por pantalla?
5. Idempotencia: si hay charge/issue, ¿aparece diseño con idempotency_key?
6. Señalá fortalezas, problemas, riesgos y recomendaciones prioritarias.
7. No inventes archivos que no estén en la evidencia del snapshot.
"""


class ReviewWorkflow(BaseWorkflow):
    """
    /review <descripción>

    Inspección del producto (TARGET) + interpretación ejecutiva.
    """

    name = "review"
    description = "Revisa arquitectura y módulos del proyecto destino."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        topic = (arguments or "").strip() or "arquitectura de módulos del proyecto"
        locale_code = detect_locale(topic)
        locale_info = resolve_locale(locale_code, engram=self._get_engram())
        locale_block = str(locale_info.get("locale_summary") or "")

        plan = ExecutionPlan(
            original_task=f"/review {topic}".strip(),
            intent="project_analysis",
            intent_category="analysis",
            objective=f"Review: {topic[:120]}",
            execution_mode="multi_step",
        )

        plan.execution_policy["max_retries"] = 1
        # Review del PRODUCTO: inspector debe usar TARGET_PROJECT_ROOT
        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["obsidian"] = True

        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.metadata["workflow"] = "review"
        # Activa SelfCritic en el engine (si respeta este flag)
        plan.metadata["requires_self_critic"] = True

        inspect = plan.add_step(
            description="Inspeccionar estructura y archivos del proyecto destino",
            unit_type="skill",
            unit_name="analyze_project",
            params={
                "path": ".",
                "task": topic,
            },
            expected_output="Snapshot / project_analysis estructurado",
            metadata={"stage": "inspection", "produces": "project_analysis"},
            timeout=90,
        )

        architect_task = (
            f"Revisión solicitada:\n{topic}\n\n"
            f"Locale (contexto regional, no inventar fisco):\n"
            f"{locale_block or 'N/A'}\n\n"
            f"{REVIEW_STANDARDS_INSTRUCTIONS}\n\n"
            "Usá la evidencia de project_analysis / architecture del contexto.\n"
            "Respondé en español, estructura clara:\n"
            "## Resumen ejecutivo\n"
            "## Componentes principales\n"
            "## Relaciones y dependencias\n"
            "## Fortalezas\n"
            "## Problemas arquitectónicos\n"
            "## Riesgos\n"
            "## Recomendaciones prioritarias\n"
        )

        architect = plan.add_step(
            description="Interpretar evidencia y generar review ejecutivo",
            unit_type="agent",
            unit_name="architect",
            params={"task": architect_task},
            expected_output="Review ejecutivo de arquitectura",
            metadata={
                "stage": "architecture_analysis",
                "consumes": "project_analysis",
            },
            timeout=180,
        )
        architect.depends_on.append(inspect.id)

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        # /review sin args es válido (review general)
        return True, ""

    def _get_engram(self) -> Any | None:
        return None
