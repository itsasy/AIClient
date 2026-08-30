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
            "locale_summary": (
                "Locale no disponible. " "No asumir país, moneda, pagos ni régimen fiscal."
            ),
            "sources": ["default"],
        }


try:
    from core.specs.paths import spec_path_for
except ImportError:

    def spec_path_for(topic: str) -> str:
        safe = re.sub(r"[^\w\s\-]", "", topic, flags=re.UNICODE)
        safe = re.sub(r"\s+", "_", safe.strip())[:80] or "spec"
        return f".specs/{safe.lower()}.md"


STANDARDS_SPEC_INSTRUCTIONS = """
Al redactar la especificación:
1. Alineá capas y módulos con Standards/Arquitectura-de-proyecto.
2. No inventes stack FE/BE salvo que el usuario lo pida explícitamente en el tema.
3. Pagos y fisco: contratos PaymentProvider / ElectronicInvoiceProvider;
   locale orienta; no hardcodees un país ni pasarela.
4. UI/vistas: Standards/UI-Design-System (un primario + tokens;
   no nueva librería UI por pantalla).
5. Si hay cobros o checkout: idempotencia (idempotency_key) según
   Standards/Pagos-e-idempotencia.
6. Criterios de hecho verificables (smokes o comportamientos observables).
7. Sección "Restricciones de estilo": una convención de naming y control de flujo
   (Standards/Estilo-de-codigo); no mezclar paradigmas sin motivo.
8. Frontend y backend del mismo producto comparten design system y contratos de dominio.
"""


class SpecWorkflow(BaseWorkflow):
    """
    /spec <descripción>

    Genera especificación formal y la persiste en .specs/

    Locale (segundo cerebro):
      Obsidian → Engram → seed packs
    """

    name = "spec"
    description = "Genera una especificación formal para una tarea."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        topic = (arguments or "").strip()
        locale_code = detect_locale(topic)

        engram = self._get_engram()
        locale_info = resolve_locale(locale_code, engram=engram)
        locale_block = str(locale_info.get("locale_summary") or "")
        locale_sources = locale_info.get("sources") or []

        safe_name = self._sanitize_name(topic) or "spec"
        try:
            spec_path = spec_path_for(topic)
        except Exception:
            spec_path = f".specs/{safe_name}.md"

        plan = ExecutionPlan(
            original_task=f"/spec {topic}".strip(),
            intent="spec",
            intent_category="documentation",
            objective=f"Especificación formal: {topic[:120]}",
            execution_mode="multi_step",
        )

        plan.execution_policy["max_retries"] = 1
        plan.governance["allow_write"] = True

        # Segundo cerebro + standards (consistencia full-stack)
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["obsidian"] = True
        plan.context_requirements["project"] = True

        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.metadata["locale_sources"] = list(locale_sources)
        plan.metadata["workflow"] = "spec"
        plan.metadata["spec_path"] = spec_path

        coding_task = self._build_spec_task(
            topic=topic,
            locale_code=locale_code,
            locale_block=locale_block,
            spec_path=spec_path,
        )

        gen = plan.add_step(
            description="Generar especificación formal (markdown)",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": coding_task,
                "path": spec_path,
            },
            expected_output="code_artifact con markdown de spec",
            metadata={
                "stage": "generation",
                "produces": "code_artifact",
            },
            timeout=180,
        )

        write = plan.add_step(
            description=f"Persistir spec en {spec_path}",
            unit_type="skill",
            unit_name="write_file",
            params={
                "path": spec_path,
                "file_index": 0,
            },
            expected_output=f"Archivo {spec_path}",
            metadata={
                "stage": "materialization",
                "consumes": "code_artifact",
            },
            timeout=60,
        )
        write.depends_on.append(gen.id)

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        if not (arguments or "").strip():
            return False, "Indicá el tema: /spec <descripción> [país=XX]"
        return True, ""

    # ------------------------------------------------------------------

    def _build_spec_task(
        self,
        topic: str,
        locale_code: str | None,
        locale_block: str,
        spec_path: str,
    ) -> str:
        locale_section = (
            f"Locale: {locale_code or 'no especificado'}\n" f"Resumen locale: {locale_block}\n"
        )
        return (
            f"Generá una especificación técnica en Markdown para:\n"
            f"{topic}\n\n"
            f"{locale_section}\n"
            f"{STANDARDS_SPEC_INSTRUCTIONS}\n\n"
            "Estructura mínima del documento:\n"
            "- Objetivo\n"
            "- Alcance (in / out)\n"
            "- Requisitos funcionales\n"
            "- Requisitos no funcionales\n"
            "- Modelo de dominio (entidades)\n"
            "- Integraciones (pagos, fisco, terceros) solo si aplica\n"
            "- UI / frontend (si aplica): layouts y vistas bajo design system\n"
            "- Arquitectura de módulos (paths sugeridos bajo src/)\n"
            "- Restricciones de estilo y stack\n"
            "- Criterio de hecho\n"
            "- Riesgos e información desconocida\n\n"
            f"Salida: code_artifact con un file path={spec_path} "
            "y content = markdown completo.\n"
            "No inventes pasarelas ni regímenes fiscales fuera del locale.\n"
            "No eleves el país a requisito funcional central si solo es contexto regional.\n"
        )

    def _get_engram(self) -> Any | None:
        """Override en el container si Engram está inyectado."""
        return None

    @staticmethod
    def _sanitize_name(topic: str) -> str:
        t = (topic or "").strip().lower()
        t = re.sub(
            r"\b(pa[ií]s|country|locale)\s*[=:]\s*[a-z]{2}\b",
            " ",
            t,
            flags=re.I,
        )
        t = re.sub(r"[^\w\s\-]", "", t, flags=re.UNICODE)
        t = re.sub(r"\s+", "_", t.strip())
        return t[:80]
