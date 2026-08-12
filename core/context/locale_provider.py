from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan

try:
    from core.locale.packs import locale_summary, list_locale_codes
except ImportError:

    def locale_summary(code: str | None) -> str:
        return ""

    def list_locale_codes() -> list[str]:
        return []


class LocaleProvider:
    """
    Inyecta resumen de locale en el contexto.
    No ejecuta nada; solo aporta conocimiento.
    """

    name = "locale"

    def provide(self, plan: ExecutionPlan) -> dict[str, Any]:
        code = (
            plan.params.get("locale")
            or plan.metadata.get("locale")
            or (plan.entities or {}).get("locale")
        )
        return {
            "locale_code": code,
            "locale_summary": locale_summary(code) if code else "",
            "available_locales": list_locale_codes(),
        }
