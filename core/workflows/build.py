from __future__ import annotations

import re
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
        return {"locale_code": code, "locale_summary": "", "sources": ["default"]}


class BuildWorkflow(BaseWorkflow):
    """
    /build <módulo|pos-stack|from-spec|ui-shell> [país=XX] [--static]
    """

    name = "build"
    description = "Scaffold de módulo(s) de producto o UI shell."

    ALLOWED = {
        "auth",
        "pos",
        "catalog",
        "cash",
        "payments",
        "invoicing",
        "delivery",
        "reports",
    }

    ALIASES = {
        "caja": "cash",
        "pago": "payments",
        "pagos": "payments",
        "factura": "invoicing",
        "facturacion": "invoicing",
        "facturación": "invoicing",
        "catalogo": "catalog",
        "catálogo": "catalog",
        "reportes": "reports",
    }

    POS_STACK = (
        "auth",
        "catalog",
        "pos",
        "cash",
        "payments",
        "invoicing",
        "delivery",
        "reports",
    )

    STACK_ALIASES = {
        "pos-stack",
        "pos_stack",
        "stack",
        "full-pos",
        "full_pos",
        "pos-completo",
    }

    SPEC_STACK_ALIASES = {
        "from-spec",
        "from_spec",
        "desde-spec",
    }

    UI_ALIASES = {
        "ui",
        "ui-shell",
        "ui_shell",
    }

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        raw = (arguments or "").strip()
        locale_code = detect_locale(raw)
        token = self._first_token(raw)

        if token in self.UI_ALIASES:
            if "--static" in raw.lower():
                return self._plan_ui_static(raw)
            return self._plan_ui_shell(raw, locale_code)

        if token in self.SPEC_STACK_ALIASES:
            return self._plan_from_spec(raw, locale_code)

        if token in self.STACK_ALIASES:
            return self._plan_stack(raw, locale_code)

        module = self._parse_module(raw)
        return self._plan_single(raw, module, locale_code)

    def validate(self, arguments: str) -> tuple[bool, str]:
        raw = (arguments or "").strip()
        if not raw:
            return (
                False,
                "Uso: /build <módulo|pos-stack|from-spec|ui-shell> [país=XX] [--static]",
            )
        token = self._first_token(raw)
        if token in self.STACK_ALIASES | self.SPEC_STACK_ALIASES | self.UI_ALIASES:
            return True, ""
        module = self._parse_module(raw)
        if module not in self.ALLOWED:
            return (
                False,
                f"Módulo '{module}' no soportado. "
                f"Permitidos: {', '.join(sorted(self.ALLOWED))}, "
                "pos-stack, from-spec, ui-shell",
            )
        return True, ""

    def _plan_single(
        self,
        raw: str,
        module: str,
        locale_code: str | None,
    ) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build {raw}".strip(),
            intent="module_scaffold",
            intent_category="development",
            objective=f"Scaffold módulo {module}",
            execution_mode="single",
        )
        plan.context_requirements["project"] = False
        plan.governance["allow_write"] = True

        params: dict[str, Any] = {"module": module}
        if locale_code:
            params["locale"] = locale_code
            plan.metadata["locale"] = locale_code
            plan.metadata["locale_sources"] = resolve_locale(locale_code).get("sources", [])

        plan.set_execution_unit(
            unit_type="skill",
            unit_name="scaffold_module",
            params=params,
        )
        plan.metadata["workflow"] = "build"
        plan.metadata["module"] = module
        return plan

    def _plan_stack(
        self,
        raw: str,
        locale_code: str | None,
        modules: tuple[str, ...] | list[str] | None = None,
    ) -> ExecutionPlan:
        stack = tuple(modules) if modules else self.POS_STACK
        plan = ExecutionPlan(
            original_task=f"/build {raw}".strip(),
            intent="module_scaffold",
            intent_category="development",
            objective="Scaffold stack POS",
            execution_mode="multi_step",
        )

        plan.metadata["aggregate_results"] = True
        plan.context_requirements["project"] = False
        plan.governance["allow_write"] = True

        if locale_code:
            plan.metadata["locale"] = locale_code
            plan.metadata["locale_sources"] = resolve_locale(locale_code).get("sources", [])

        prev_id: str | None = None
        for module in stack:
            params: dict[str, Any] = {"module": module}
            if locale_code and module in {"payments", "invoicing"}:
                params["locale"] = locale_code
            step = plan.add_step(
                description=f"Scaffold módulo {module}",
                unit_type="skill",
                unit_name="scaffold_module",
                params=params,
                expected_output=f"Estructura base de {module}",
                metadata={"stage": "scaffold", "module": module},
            )
            if prev_id:
                step.depends_on.append(prev_id)
            prev_id = step.id

        plan.metadata["workflow"] = "build"
        plan.metadata["module"] = "pos-stack"
        return plan

    def _plan_from_spec(
        self,
        raw: str,
        locale_code: str | None,
    ) -> ExecutionPlan:
        root = Path(getattr(Config, "TARGET_PROJECT_ROOT", Path.cwd()))
        specs_dir = root / ".specs"
        modules: list[str] = list(self.POS_STACK)
        spec_text = ""
        spec_name = ""

        if specs_dir.is_dir():
            files = sorted(
                list(specs_dir.glob("*.md")) + list(specs_dir.glob("*.json")),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            rest = re.sub(
                r"^(from-spec|from_spec|desde-spec)\s*",
                "",
                raw.strip(),
                flags=re.I,
            )
            tokens = {t.lower() for t in rest.split() if len(t) > 2}
            chosen = None
            for path in files:
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if tokens and not any(
                    t in path.stem.lower() or t in text.lower()[:3000] for t in tokens
                ):
                    continue
                chosen = path
                spec_text = text
                break
            if chosen is None and files:
                chosen = files[0]
                try:
                    spec_text = chosen.read_text(encoding="utf-8")
                except OSError:
                    spec_text = ""
            if chosen is not None:
                spec_name = chosen.name

        inferred = self._modules_from_spec(spec_text)
        if inferred:
            modules = inferred
        if not locale_code and spec_text:
            locale_code = detect_locale(spec_text)

        plan = self._plan_stack(raw, locale_code, modules=modules)
        plan.metadata["from_spec"] = spec_name or True
        plan.metadata["aggregate_results"] = True
        plan.objective = f"Scaffold desde spec {spec_name or '(última)'}"
        return plan

    def _plan_ui_static(self, raw: str) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build {raw}".strip(),
            intent="ui_scaffold",
            intent_category="frontend",
            objective="UI shell estática (fallback)",
            execution_mode="single",
        )
        plan.context_requirements["project"] = False
        plan.governance["allow_write"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="scaffold_ui_shell",
            params={},
        )
        plan.metadata["workflow"] = "build"
        plan.metadata["module"] = "ui-shell-static"
        return plan

    def _plan_ui_shell(
        self,
        raw: str,
        locale_code: str | None,
    ) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build {raw}".strip(),
            intent="ui_scaffold",
            intent_category="frontend",
            objective="Generar UI shell POS con IA",
            execution_mode="multi_step",
        )
        plan.context_requirements["project"] = False
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["spec"] = True
        plan.governance["allow_write"] = True

        locale_hint = ""
        if locale_code:
            plan.metadata["locale"] = locale_code
            info = resolve_locale(locale_code)
            locale_hint = str(info.get("locale_summary") or "")
            plan.metadata["locale_sources"] = info.get("sources", [])

        prompt = f"""
Genera una UI POS limpia (login centrado, sidebar operativa, dashboard con KPIs).

Si en el contexto hay standards o notas UI-POS-Shell, síguelas con prioridad.
No copies un diseño de un solo país; labels/moneda según LOCALE.

Entrega UN ÚNICO JSON code_artifact:
{{
  "type": "code_artifact",
  "files": [
    {{"path": "src/ui/pos_shell/login.html", "content": "..."}},
    {{"path": "src/ui/pos_shell/shell.html", "content": "..."}},
    {{"path": "src/ui/pos_shell/dashboard.html", "content": "..."}},
    {{"path": "src/ui/pos_shell/pos.css", "content": "..."}}
  ]
}}

Reglas:
- Un color primario + neutros; CTA claro.
- Sidebar: Operación / Catálogo / Gestión.
- Login: card, recordarme, estado terminal, versión.
- Dashboard: KPIs + tabla recientes.
- Si el proyecto es React/Vue/Next y está en contexto, genera ese stack.
- SOLO JSON válido, sin markdown envolvente.

LOCALE:
{locale_hint or "No asumir país ni moneda concreta."}
""".strip()

        gen = plan.add_step(
            description="Generar UI shell POS",
            unit_type="agent",
            unit_name="coder",
            params={"task": prompt, "mode": "ui_shell"},
            expected_output="code_artifact con archivos UI",
            metadata={"stage": "generation", "produces": "code_artifact"},
        )

        for index, rel in enumerate(
            (
                "src/ui/pos_shell/login.html",
                "src/ui/pos_shell/shell.html",
                "src/ui/pos_shell/dashboard.html",
                "src/ui/pos_shell/pos.css",
            )
        ):
            write = plan.add_step(
                description=f"Escribir {rel}",
                unit_type="skill",
                unit_name="write_file",
                params={"path": rel, "file_index": index},
                expected_output=f"Archivo {rel}",
                metadata={"stage": "materialization", "consumes": "code_artifact"},
            )
            write.depends_on.append(gen.id)

        plan.metadata["workflow"] = "build"
        plan.metadata["module"] = "ui-shell"
        return plan

    def _modules_from_spec(self, text: str) -> list[str]:
        if not text:
            return []
        lower = text.lower()

        # Spec de producto POS → stack completo (o casi)
        if (
            any(
                k in lower
                for k in (
                    "punto de venta",
                    " pos",
                    "pos ",
                    "restaurante",
                    "multiestación",
                    "multiestacion",
                    "offline",
                )
            )
            or "pos_" in lower
        ):
            return list(self.POS_STACK)

        keywords = {
            "auth": ("auth", "autentic", "login", "jwt", "sesión", "sesion"),
            "catalog": ("catalog", "producto", "menú", "menu", "precio"),
            "pos": ("punto de venta", " ticket", "pedido", "turno"),
            "cash": ("caja", "cash", "cierre de caja"),
            "payments": ("pago", "payment", "pasarela", "cobro"),
            "invoicing": ("factura", "invoice", "afip", "cfdi", "fiscal"),
            "delivery": ("delivery", "envio", "envío", "reparto"),
            "reports": ("reporte", "report", "historial de ventas"),
        }
        found = [mod for mod, keys in keywords.items() if any(k in lower for k in keys)]
        return [m for m in self.POS_STACK if m in found]

    def _first_token(self, raw: str) -> str:
        cleaned = re.sub(
            r"\b(pa[ií]s|country|locale)\s*[=:]\s*[A-Za-z]{2}\b",
            " ",
            raw,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"--static", " ", cleaned, flags=re.I)
        return (cleaned.split() or [""])[0].strip().lower()

    def _parse_module(self, raw: str) -> str:
        token = self._first_token(raw)
        return self.ALIASES.get(token, token)
