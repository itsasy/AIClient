from __future__ import annotations

import re
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
            "locale_summary": "Locale no disponible.",
            "sources": ["default"],
        }


PLAN_STANDARDS_INSTRUCTIONS = """
Al redactar el plan de implementación:
1. Respetá Standards/Arquitectura-de-proyecto (capas domain/adapters/ui).
2. Ordená pasos: dominio → contratos/adapters → UI → smokes.
3. No inventes stack no pedido.
4. Pagos/fisco solo vía contratos; locale orienta.
5. UI bajo UI-Design-System; reutilizar shell si existe.
6. Cada paso debe ser accionable (/build, enrich, o path de archivo).
7. Incluí verificación (smoke) al final.
"""


class PlanWorkflow(BaseWorkflow):
    name = "plan"
    description = "Genera un plan de implementación formal."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        topic = (arguments or "").strip()
        locale_code = detect_locale(topic)
        locale_info = resolve_locale(locale_code, engram=self._get_engram())
        locale_block = str(locale_info.get("locale_summary") or "")

        safe = re.sub(r"[^\w\s\-]", "", topic, flags=re.UNICODE)
        safe = re.sub(r"\s+", "_", safe.strip().lower())[:60] or "plan"
        plan_path = f".specs/plan_{safe}.md"

        plan = ExecutionPlan(
            original_task=f"/plan {topic}".strip(),
            intent="planning",
            intent_category="documentation",
            objective=f"Plan de implementación: {topic[:120]}",
            execution_mode="multi_step",
        )
        plan.execution_policy["max_retries"] = 1
        plan.governance["allow_write"] = True
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["obsidian"] = True
        plan.context_requirements["project"] = True
        plan.context_requirements["gentleman"] = True
        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.metadata["workflow"] = "plan"

        task = (
            f"Generá un plan de implementación en Markdown para:\n{topic}\n\n"
            f"Locale: {locale_code or 'N/A'}\n{locale_block}\n\n"
            f"{PLAN_STANDARDS_INSTRUCTIONS}\n\n"
            "Formato:\n"
            "## Objetivo\n## Pasos ordenados\n"
            "## Módulos/paths afectados\n## Dependencias\n"
            "## Riesgos\n## Verificación (smokes)\n\n"
            f"Salida: code_artifact path={plan_path}, content=markdown.\n"
        )

        gen = plan.add_step(
            description="Generar plan de implementación",
            unit_type="agent",
            unit_name="coder",
            params={"task": task, "path": plan_path},
            metadata={"stage": "generation", "produces": "code_artifact"},
            timeout=180,
        )
        write = plan.add_step(
            description=f"Escribir {plan_path}",
            unit_type="skill",
            unit_name="write_file",
            params={"path": plan_path, "file_index": 0},
            metadata={"stage": "materialization", "consumes": "code_artifact"},
            timeout=60,
        )
        write.depends_on.append(gen.id)
        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        if not (arguments or "").strip():
            return False, "Indicá el tema: /plan <descripción>"
        return True, ""

    def _get_engram(self) -> Any | None:
        return None
