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
        return {
            "locale_code": code,
            "locale_summary": "",
            "sources": ["default"],
        }


ENRICH_CONSTRAINTS = """
CONSTRAINTS (obligatorio):
- Respetar Standards del contexto: Arquitectura-de-proyecto, Estilo-de-codigo,
  UI-Design-System, Pagos-e-idempotencia / Pagos-y-facturacion.
- Reutilizar services y contratos existentes (PaymentsService, protocols);
  no duplicar cobros ni facturación en la vista o en otro service.
- Mismo estilo de control de flujo y naming que el proyecto; no mezclar paradigmas.
- Operaciones de pago/facturación: diseño idempotente (idempotency_key en metadata).
- No inventar framework, ORM ni librería UI no pedidos en la tarea/spec.
- No importar core/llm/runtime del orquestador AIClient.
- Frontend: un primario + tokens; reutilizar layouts/componentes si existen en el repo.
"""


class BuildWorkflow(BaseWorkflow):
    """
    /build <módulo|*-stack|from-spec|ui-shell|enrich ...> [país=XX] [--static]
    """

    name = "build"
    description = "Scaffold de módulos, UI shell o enrich de dominio/UI."

    ALLOWED = {
        "auth",
        "pos",
        "catalog",
        "cash",
        "payments",
        "invoicing",
        "delivery",
        "reports",
        "patients",
        "agenda",
        "odontogram",
        "clinical_history",
        "prescriptions",
        "inventory",
        "reservations",
        "dashboard",
        "sales",
        "tasks",
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
        "pacientes": "patients",
        "odontograma": "odontogram",
        "reservas": "reservations",
        "tareas": "tasks",
        "ventas": "sales",
    }

    VERTICAL_STACKS: dict[str, tuple[str, ...]] = {
        "pos": (
            "auth",
            "catalog",
            "pos",
            "cash",
            "payments",
            "invoicing",
            "delivery",
            "reports",
        ),
        "dental": (
            "auth",
            "patients",
            "agenda",
            "odontogram",
            "clinical_history",
            "prescriptions",
            "payments",
            "inventory",
            "reports",
        ),
        "restaurant": (
            "auth",
            "catalog",
            "reservations",
            "dashboard",
            "sales",
            "tasks",
            "reports",
        ),
    }

    STACK_ALIASES = frozenset(
        {
            "pos-stack",
            "pos_stack",
            "stack",
            "full-stack",
            "fullstack",
            "dental-stack",
            "dental_stack",
            "restaurant-stack",
            "restaurant_stack",
            "resto-stack",
        }
    )

    ENRICH_DOMAIN_HINTS = {
        "pos": (
            "Pedidos en memoria, líneas desde catálogo (SKU), total, pay/close. "
            "Sin SDKs de pago ni AFIP."
        ),
        "catalog": (
            "Productos con SKU, nombre, precio, activo; add/update/get/list/deactivate. "
            "Sin órdenes ni pagos."
        ),
        "cash": "Apertura/cierre de caja, movimientos, saldo; todo en memoria.",
        "auth": "Registro/login/logout con hash local simple; sin framework JWT inventado.",
        "payments": "PaymentsService delega en PaymentProvider; factory + mock; idempotency_key.",
        "invoicing": "InvoicingService delega en ElectronicInvoiceProvider; factory + mock.",
        "delivery": "Envíos/estados de entrega en memoria.",
        "reports": "Resúmenes de ventas / listados simples en memoria.",
        "patients": "Ficha de paciente id/nombre/documento/teléfono; CRUD en memoria.",
        "agenda": "Turnos schedule/list/set_status en memoria.",
        "odontogram": "Hallazgos por pieza y cara; summary por paciente.",
        "clinical_history": "Notas de evolución por paciente.",
        "prescriptions": "Recetas simples en memoria.",
        "inventory": "Insumos cantidad/mínimo en memoria.",
        "reservations": "Reservas mesa/hora/pax en memoria.",
        "dashboard": "KPIs y listados para panel restaurant (o delegar en facade).",
        "sales": "Líneas de venta producto/categoría/monto.",
        "tasks": "Tareas pendientes prioridad/done.",
    }

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        raw = (arguments or "").strip()
        locale_code = detect_locale(raw)
        locale_info = resolve_locale(locale_code, engram=self._get_engram())
        locale_summary = str(locale_info.get("locale_summary") or "")
        lower = raw.lower()
        static = "--static" in lower

        # --- enrich ---
        if re.search(r"\benrich\b", lower):
            if re.search(r"pos-?stack|stack completo|full.?stack", lower):
                return self._plan_enrich_stack(
                    raw, locale_code, locale_summary, modules=("catalog", "pos", "cash")
                )
            module = self._parse_module(re.sub(r"\benrich\b", " ", raw, flags=re.I))
            if module in self.ALLOWED:
                return self._plan_enrich_module(module, raw, locale_code, locale_summary)
            return self._plan_enrich_stack(
                raw, locale_code, locale_summary, modules=("catalog", "pos", "cash")
            )

        # --- ui-shell ---
        if re.search(r"\bui-?shell\b", lower):
            variant = "pos"
            if re.search(r"\bdental\b", lower):
                variant = "dental"
            elif re.search(r"\b(restaurant|restó|resto)\b", lower):
                variant = "restaurant"
            if static:
                return self._plan_ui_shell_static(raw, locale_code, variant=variant)
            return self._plan_ui_shell(raw, locale_code, locale_summary, variant=variant)

        # --- from-spec ---
        if re.search(r"\b(from-spec|from_spec|desde-spec)\b", lower):
            return self._plan_from_spec(raw, locale_code)

        # --- vertical stacks ---
        for vname, vmodules in self.VERTICAL_STACKS.items():
            if re.search(rf"\b{re.escape(vname)}-?stack\b", lower):
                return self._plan_scaffold_modules(list(vmodules), raw, locale_code)

        token = self._first_token(raw)
        if token in self.STACK_ALIASES:
            if "dental" in token:
                return self._plan_scaffold_modules(
                    list(self.VERTICAL_STACKS["dental"]), raw, locale_code
                )
            if "restaurant" in token or "resto" in token:
                return self._plan_scaffold_modules(
                    list(self.VERTICAL_STACKS["restaurant"]), raw, locale_code
                )
            return self._plan_scaffold_modules(list(self.VERTICAL_STACKS["pos"]), raw, locale_code)

        # --- single module ---
        module = self._parse_module(raw)
        if module in self.ALLOWED:
            return self._plan_scaffold_module(module, raw, locale_code)

        guessed = self._guess_modules_from_text(raw)
        if len(guessed) > 1:
            return self._plan_scaffold_modules(guessed, raw, locale_code)
        if len(guessed) == 1:
            return self._plan_scaffold_module(guessed[0], raw, locale_code)

        return self._plan_scaffold_modules(list(self.VERTICAL_STACKS["pos"]), raw, locale_code)

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""

    # =========================================================
    # Scaffold
    # =========================================================

    def _plan_scaffold_module(
        self,
        module: str,
        raw: str,
        locale_code: str | None,
    ) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build {module}",
            intent="module_scaffold",
            intent_category="code",
            objective=f"Scaffold módulo {module}",
            execution_mode="single",
        )
        plan.governance["allow_write"] = True
        plan.context_requirements["project"] = False
        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="scaffold_module",
            params={"module": module, "locale": locale_code or ""},
        )
        plan.metadata["workflow"] = "build"
        return plan

    def _plan_scaffold_modules(
        self,
        modules: list[str],
        raw: str,
        locale_code: str | None,
    ) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build {raw}",
            intent="module_scaffold",
            intent_category="code",
            objective="Scaffold módulos",
            execution_mode="multi_step",
        )
        plan.governance["allow_write"] = True
        plan.execution_policy["stop_on_error"] = False
        plan.context_requirements["project"] = False
        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.metadata["aggregate_results"] = True
        plan.metadata["workflow"] = "build"

        for mod in modules:
            plan.add_step(
                description=f"Scaffold {mod}",
                unit_type="skill",
                unit_name="scaffold_module",
                params={"module": mod, "locale": locale_code or ""},
                expected_output=f"Módulo {mod}",
                metadata={"module": mod},
                timeout=60,
            )
        return plan

    def _plan_ui_shell_static(
        self,
        raw: str,
        locale_code: str | None,
        variant: str = "pos",
    ) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build ui-shell {variant} --static",
            intent="ui_scaffold",
            intent_category="code",
            objective=f"UI shell {variant} estático",
            execution_mode="single",
        )
        plan.governance["allow_write"] = True
        plan.context_requirements["project"] = False
        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="scaffold_ui_shell",
            params={"variant": variant, "locale": locale_code or ""},
        )
        plan.metadata["workflow"] = "build"
        return plan

    def _plan_ui_shell(
        self,
        raw: str,
        locale_code: str | None,
        locale_summary: str,
        variant: str = "pos",
    ) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build ui-shell {raw}",
            intent="ui_scaffold",
            intent_category="code",
            objective=f"Generar UI shell {variant}",
            execution_mode="multi_step",
        )
        plan.execution_policy["max_retries"] = 1
        plan.governance["allow_write"] = True
        plan.context_requirements["project"] = False
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True
        if locale_code:
            plan.metadata["locale"] = locale_code

        base = {
            "pos": "src/ui/pos_shell",
            "dental": "src/ui/dental_shell",
            "restaurant": "src/ui/restaurant_shell",
        }.get(variant, "src/ui/pos_shell")

        task = (
            f"{raw}\n\n"
            f"Generá shell UI variant={variant} bajo {base}/ "
            f"(login, shell, vista principal, css, README).\n"
            f"Priorizá Standards/UI-Design-System y notas UI del vertical.\n"
            f"Locale: {locale_summary or locale_code or 'no asumir país'}\n"
            f"{ENRICH_CONSTRAINTS}\n"
            "Salida: code_artifact con varios files.\n"
        )
        gen = plan.add_step(
            description="Generar UI shell",
            unit_type="agent",
            unit_name="coder",
            params={"task": task, "path": f"{base}/shell.html"},
            metadata={"stage": "generation", "produces": "code_artifact"},
            timeout=180,
        )
        write = plan.add_step(
            description="Materializar UI shell",
            unit_type="skill",
            unit_name="write_file",
            params={"write_all": True},
            metadata={"stage": "materialization", "consumes": "code_artifact"},
            timeout=60,
        )
        write.depends_on.append(gen.id)
        plan.metadata["workflow"] = "build"
        return plan

    def _plan_from_spec(
        self,
        raw: str,
        locale_code: str | None,
    ) -> ExecutionPlan:
        modules = self._modules_from_specs(raw)
        if not modules:
            modules = list(self.VERTICAL_STACKS["pos"])
        plan = self._plan_scaffold_modules(modules, raw, locale_code)
        plan.metadata["from_spec"] = True
        return plan

    # =========================================================
    # Enrich
    # =========================================================

    def _plan_enrich_module(
        self,
        module: str,
        raw: str,
        locale_code: str | None,
        locale_summary: str = "",
    ) -> ExecutionPlan:
        target = f"src/modules/{module}/service.py"
        hint = self.ENRICH_DOMAIN_HINTS.get(module, f"Servicio de dominio {module}.")

        plan = ExecutionPlan(
            original_task=f"/build enrich {module}",
            intent="code_generation",
            intent_category="code",
            objective=f"Enriquecer {target}",
            execution_mode="multi_step",
        )
        plan.execution_policy["max_retries"] = 1
        plan.execution_policy["stop_on_error"] = True
        plan.governance["allow_write"] = True
        plan.context_requirements["project"] = False
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True
        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.metadata["workflow"] = "build"
        plan.metadata["enrich"] = module

        task = (
            f"{raw}\n\n"
            f"Reescribe {target} con dominio usable en memoria.\n"
            f"{hint}\n"
            f"Locale orientativo: {locale_summary or locale_code or 'N/A'}\n"
            f"{ENRICH_CONSTRAINTS}\n"
            "Python 3.11+, type hints.\n"
            f"Salida: code_artifact path={target}."
        )
        gen = plan.add_step(
            description=f"Generar {target}",
            unit_type="agent",
            unit_name="coder",
            params={"task": task, "path": target},
            expected_output="code_artifact",
            metadata={"stage": "generation", "produces": "code_artifact"},
            timeout=180,
        )
        write = plan.add_step(
            description=f"Escribir {target}",
            unit_type="skill",
            unit_name="write_file",
            params={"path": target, "file_index": 0},
            expected_output=f"Archivo {target}",
            metadata={"stage": "materialization", "consumes": "code_artifact"},
            timeout=60,
        )
        write.depends_on.append(gen.id)
        return plan

    def _plan_enrich_stack(
        self,
        raw: str,
        locale_code: str | None,
        locale_summary: str = "",
        modules: tuple[str, ...] = ("catalog", "pos", "cash"),
    ) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build enrich stack {raw}",
            intent="code_generation",
            intent_category="code",
            objective="Enriquecer módulos en memoria",
            execution_mode="multi_step",
        )
        plan.execution_policy["max_retries"] = 1
        plan.execution_policy["stop_on_error"] = True
        plan.governance["allow_write"] = True
        plan.context_requirements["project"] = False
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True
        if locale_code:
            plan.metadata["locale"] = locale_code
        plan.metadata["workflow"] = "build"
        plan.metadata["enrich"] = "stack"

        prev_id: str | None = None
        for mod in modules:
            target = f"src/modules/{mod}/service.py"
            hint = self.ENRICH_DOMAIN_HINTS.get(mod, "")
            gen = plan.add_step(
                description=f"Enrich generar {mod}",
                unit_type="agent",
                unit_name="coder",
                params={
                    "path": target,
                    "task": (
                        f"Enriquecer {target}. {hint}\n{raw}\n"
                        f"Locale: {locale_summary or locale_code or ''}\n"
                        f"{ENRICH_CONSTRAINTS}\n"
                        "code_artifact con ese path."
                    ),
                },
                metadata={"stage": "generation", "module": mod},
                timeout=180,
            )
            write = plan.add_step(
                description=f"Enrich escribir {mod}",
                unit_type="skill",
                unit_name="write_file",
                params={"path": target, "file_index": 0},
                metadata={"stage": "materialization", "module": mod},
                timeout=60,
            )
            write.depends_on.append(gen.id)
            if prev_id:
                gen.depends_on.append(prev_id)
            prev_id = write.id

        return plan

    # =========================================================
    # Helpers
    # =========================================================

    def _get_engram(self) -> Any | None:
        return None

    def _first_token(self, raw: str) -> str:
        cleaned = re.sub(
            r"\b(pa[ií]s|country|locale)\s*[=:]\s*[A-Za-z]{2}\b",
            " ",
            raw,
            flags=re.I,
        )
        cleaned = re.sub(r"--static", " ", cleaned, flags=re.I)
        cleaned = re.sub(r"\benrich\b", " ", cleaned, flags=re.I)
        return (cleaned.split() or [""])[0].strip().lower()

    def _parse_module(self, raw: str) -> str:
        token = self._first_token(raw)
        return self.ALIASES.get(token, token)

    def _guess_modules_from_text(self, raw: str) -> list[str]:
        lower = raw.lower()
        keywords = {
            "auth": ("auth", "autentic", "login", "jwt"),
            "catalog": ("catalog", "producto", "menú", "menu"),
            "pos": ("punto de venta", "pedido", "ticket"),
            "cash": ("caja", "cash", "cierre de caja"),
            "payments": ("pago", "payment", "pasarela", "cobro"),
            "invoicing": ("factura", "invoice", "afip", "cfdi", "fiscal"),
            "delivery": ("delivery", "envío", "envio", "reparto"),
            "reports": ("reporte", "report", "historial de ventas"),
            "patients": ("paciente", "patient"),
            "agenda": ("agenda", "turno", "cita"),
            "odontogram": ("odontogram", "odontograma", "pieza dental"),
        }
        found = [m for m, keys in keywords.items() if any(k in lower for k in keys)]
        order = list(self.VERTICAL_STACKS["pos"]) + list(self.VERTICAL_STACKS["dental"])
        seen: list[str] = []
        for m in order:
            if m in found and m not in seen:
                seen.append(m)
        return seen

    def _modules_from_specs(self, raw: str) -> list[str]:
        root = Path(getattr(Config, "TARGET_PROJECT_ROOT", Path.cwd()))
        specs = root / ".specs"
        if not specs.is_dir():
            return self._guess_modules_from_text(raw) or list(self.VERTICAL_STACKS["pos"])

        files = sorted(
            list(specs.glob("*.md")) + list(specs.glob("*.json")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return list(self.VERTICAL_STACKS["pos"])

        try:
            text = files[0].read_text(encoding="utf-8", errors="ignore")[:8000]
        except OSError:
            return list(self.VERTICAL_STACKS["pos"])

        lower = (text + " " + raw).lower()
        if "dental" in lower or "odontogram" in lower:
            return list(self.VERTICAL_STACKS["dental"])
        if "restaurant" in lower or "reserva" in lower:
            return list(self.VERTICAL_STACKS["restaurant"])
        if "pos" in lower or "punto de venta" in lower:
            return list(self.VERTICAL_STACKS["pos"])
        return self._guess_modules_from_text(lower) or list(self.VERTICAL_STACKS["pos"])
