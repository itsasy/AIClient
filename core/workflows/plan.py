from __future__ import annotations

from pathlib import Path
from typing import Any

from core.commands.workflow import BaseWorkflow
from core.config import Config
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


class PlanWorkflow(BaseWorkflow):
    """
    /plan [descripción]

    Plan legible basado en:
      - Specs en .specs/
      - Locale (Obsidian → Engram → seed)
      - Contexto ligero (sin snapshot de proyecto completo)
    """

    name = "plan"
    description = "Genera un plan de ejecución para la tarea actual."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        topic = (arguments or "").strip() or "la tarea actual del proyecto"
        specs_excerpt = self._load_related_specs(topic)
        locale_code = detect_locale(topic)

        engram = None
        try:
            from core.engram_memory import EngramMemory

            engram = EngramMemory()
        except Exception:
            pass

        locale_info = resolve_locale(locale_code, engram=engram)

        plan = ExecutionPlan(
            original_task=f"/plan {topic}" if arguments else "/plan",
            intent="planning",
            intent_category="planning",
            objective=f"Generar plan de ejecución para: {topic}",
            execution_mode="single",
        )

        plan.context_requirements["project"] = False
        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True
        plan.context_requirements["spec"] = True

        plan.set_execution_unit(
            unit_type="agent",
            unit_name="task_agent",
            params={
                "task": self._build_task(topic, specs_excerpt, locale_info),
                "mode": "planning",
            },
        )

        plan.metadata["requires_self_critic"] = False
        plan.metadata["workflow"] = "plan"
        plan.metadata["specs_loaded"] = bool(specs_excerpt)
        if locale_code:
            plan.metadata["locale"] = locale_code
            plan.metadata["locale_sources"] = locale_info.get("sources", [])

        topic_l = topic.lower()
        if any(
            k in topic_l
            for k in (
                "jwt",
                "auth",
                "login",
                "autentic",
                "sesión",
                "sesion",
                "oauth",
                "password",
                "contraseña",
            )
        ):
            plan.context_requirements["standards"] = False

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""

    def _build_task(
        self,
        topic: str,
        specs_excerpt: str,
        locale_info: dict[str, Any],
    ) -> str:
        parts = [
            f"Elabora un plan de ejecución paso a paso para: {topic}.",
            "",
            "Reglas obligatorias:",
            "- Basa el plan en la especificación si existe abajo.",
            "- NO inventes stack ni framework (Vue, React, Next, Laravel, Django,",
            "  microservicios, etc.) si no está en el spec o en el pedido del usuario.",
            "- Si el contexto trae standards de frontend u otro dominio, IGNÓRALOS",
            "  cuando el tema no los pida (p. ej. plan de JWT/auth ≠ adoptar Vue).",
            "- NO inventes módulos o integraciones que el spec no mencione.",
            "- Locale: solo aplica moneda/pagos/fisco si el tema o el spec lo requieren.",
            "  No conviertas un plan de auth/JWT en un plan de pagos o AFIP.",
            "- Sé concreto: pasos, orden, dependencias, criterios de hecho.",
            "- No ejecutes nada; solo planifica.",
            "- No añadas notas del estilo «se usa Vue según standards» salvo pedido explícito.",
            "",
            "Formato:",
            "1. Objetivo",
            "2. Pasos numerados",
            "3. Dependencias",
            "4. Riesgos",
            "5. Criterio de hecho",
        ]

        locale_code = locale_info.get("locale_code")
        locale_summary = locale_info.get("locale_summary") or ""
        if locale_code or locale_summary:
            parts.extend(
                [
                    "",
                    f"=== LOCALE ({locale_code or 'n/a'}) — contexto, no mandato de producto ===",
                    locale_summary,
                    "=== FIN LOCALE ===",
                ]
            )

        if specs_excerpt:
            parts.extend(
                [
                    "",
                    "=== ESPECIFICACIONES RELACIONADAS ===",
                    specs_excerpt[:12000],
                    "=== FIN SPECS ===",
                ]
            )
        else:
            parts.extend(
                [
                    "",
                    "No hay spec en .specs/ para este tema.",
                    "Planifica en genérico y marca supuestos explícitos.",
                    "No inventes stack.",
                ]
            )

        return "\n".join(parts)

    def _load_related_specs(self, topic: str) -> str:
        root = Path(getattr(Config, "TARGET_PROJECT_ROOT", Path.cwd()))
        specs_dir = root / ".specs"
        if not specs_dir.is_dir():
            return ""

        tokens = {
            t.lower() for t in topic.replace("/", " ").replace("-", " ").split() if len(t) > 2
        }
        chunks: list[str] = []

        files = list(specs_dir.glob("*.md")) + list(specs_dir.glob("*.json"))
        for path in sorted(files):
            name = path.stem.lower()
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            score = sum(1 for t in tokens if t in name or t in text.lower()[:2000])
            if tokens and score == 0:
                continue
            chunks.append(f"--- {path.name} ---\n{text[:4000]}")
            if len(chunks) >= 3:
                break

        if not chunks:
            recent = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
            for path in recent[:2]:
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                chunks.append(f"--- {path.name} ---\n{text[:4000]}")

        return "\n\n".join(chunks)
