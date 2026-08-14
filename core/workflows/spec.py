from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan
from core.locale.detect import detect_locale
from core.specs.paths import spec_path_for

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


class SpecWorkflow(BaseWorkflow):
    """
    /spec <descripción>

    Genera especificación formal y la persiste en .specs/

    Locale (segundo cerebro):
      Obsidian → Engram → seed packs.py
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

        spec_path = spec_path_for(topic)

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
        if locale_code:
            plan.params["locale"] = locale_code
            plan.metadata["locale"] = locale_code
        plan.metadata["locale_sources"] = locale_info.get("sources", [])

        generate = plan.add_step(
            description=f"Generar especificación para: {topic}",
            unit_type="agent",
            unit_name="task_agent",
            params={
                "task": self._build_spec_prompt(topic, locale_code, locale_block),
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
            params={"path": spec_path},
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

    def _get_engram(self) -> Any | None:
        try:
            from core.engram_memory import EngramMemory

            return EngramMemory()
        except Exception:
            return None

    def _build_spec_prompt(
        self,
        topic: str,
        locale_code: str | None,
        locale_block: str,
    ) -> str:
        lines = [
            f"Redacta una especificación técnica clara y completa para: {topic}.",
            "",
            "Incluye secciones:",
            "1. Objetivo",
            "2. Alcance (in / out)",
            "3. Requisitos funcionales",
            "4. Requisitos no funcionales",
            "5. Modelo de dominio (entidades principales)",
            "6. Integraciones (pagos, facturación, terceros) — solo si aplica al tema",
            "7. Criterios de aceptación",
            "8. Riesgos y supuestos",
            "",
            "Reglas obligatorias:",
            "- Responde SOLO con Markdown, sin preámbulos.",
            "- NO inventes framework ni stack (Vue, React, Next, Laravel, Django, microservicios)",
            "  salvo que el usuario lo pida explícitamente en el tema.",
            "- NO inventes módulos de negocio que el tema no pida.",
            "- Pagos y facturación: solo como interfaces/adapters si el tema es POS, cobros o fisco.",
            "- Si el tema es autenticación, JWT, smoke de locale u otra cosa acotada:",
            "  no conviertas la spec en un diseño completo de POS ni de pasarelas.",
            "- El bloque LOCALE es contexto regional. Úsalo así:",
            "  · Tema de pagos/POS/fisco → aplica moneda, medios de pago y régimen fiscal del locale.",
            "  · Tema ajeno (auth, JWT, smoke, infra) → puedes citar país/moneda en una línea de contexto;",
            "    NO los eleves a requisitos funcionales centrales ni a integraciones obligatorias.",
            "- Si no hay LOCALE, no asumas país ni pasarela.",
        ]

        if locale_code or locale_block:
            lines.extend(
                [
                    "",
                    f"=== LOCALE ({locale_code or 'n/a'}) ===",
                    locale_block,
                    "=== FIN LOCALE ===",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "=== LOCALE ===",
                    "No especificado. No asumir país, moneda, pagos ni régimen fiscal.",
                    "=== FIN LOCALE ===",
                ]
            )

        return "\n".join(lines)
