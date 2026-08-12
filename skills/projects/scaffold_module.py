from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.config import Config
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from skills.base import Skill


class ScaffoldModuleSkill(Skill):
    """
    Esqueleto de módulo de producto + adapters por locale (payments/invoicing).
    No llama al LLM.
    """

    name = "scaffold_module"
    description = "Scaffold de módulo de producto (auth, pos, payments, ...)."
    version = "1.1"
    capabilities = (
        "module_scaffold",
        "pos_module",
        "project_structure",
    )

    ALLOWED_MODULES = {
        "auth": ("src/modules/auth", ("__init__.py", "service.py", "routes.py")),
        "pos": ("src/modules/pos", ("__init__.py", "service.py", "routes.py")),
        "catalog": ("src/modules/catalog", ("__init__.py", "service.py", "routes.py")),
        "cash": ("src/modules/cash", ("__init__.py", "service.py", "routes.py")),
        "payments": (
            "src/modules/payments",
            ("__init__.py", "provider.py", "service.py"),
        ),
        "invoicing": (
            "src/modules/invoicing",
            ("__init__.py", "provider.py", "service.py"),
        ),
        "delivery": ("src/modules/delivery", ("__init__.py", "service.py")),
        "reports": ("src/modules/reports", ("__init__.py", "service.py")),
    }

    INTERFACE_STUBS = {
        "payments": """from __future__ import annotations

from typing import Any, Protocol


class PaymentProvider(Protocol):
    def list_methods(self, locale: str) -> list[dict[str, Any]]:
        ...

    def charge(
        self,
        amount: float,
        currency: str,
        method: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def refund(
        self,
        payment_id: str,
        amount: float | None = None,
    ) -> dict[str, Any]:
        ...
""",
        "invoicing": """from __future__ import annotations

from typing import Any, Protocol


class ElectronicInvoiceProvider(Protocol):
    def issue(
        self,
        ticket: dict[str, Any],
        customer: dict[str, Any] | None,
        locale: str,
    ) -> dict[str, Any]:
        ...

    def cancel(self, invoice_id: str, reason: str) -> dict[str, Any]:
        ...

    def status(self, invoice_id: str) -> dict[str, Any]:
        ...
""",
    }

    PAYMENT_ADAPTERS = {
        "AR": ("mercadopago.py", "MercadoPagoProvider"),
        "PE": ("local_wallet.py", "LocalWalletProvider"),
        "MX": ("conekta.py", "ConektaProvider"),
        "ES": ("redsys.py", "RedsysProvider"),
        "CL": ("webpay.py", "WebpayProvider"),
        "CO": ("pse.py", "PseProvider"),
    }

    INVOICE_ADAPTERS = {
        "AR": ("afip.py", "AfipInvoiceProvider"),
        "MX": ("cfdi.py", "CfdiInvoiceProvider"),
        "ES": ("verifactu.py", "VerifactuInvoiceProvider"),
        "CL": ("sii_dte.py", "SiiDteProvider"),
        "CO": ("dian.py", "DianInvoiceProvider"),
        "PE": ("boleta_local.py", "BoletaLocalProvider"),
    }

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not plan.allows_write():
            return self._error("Escritura no permitida por governance.")

        params = dict(step.params or {})
        module = str(params.get("module") or "").strip().lower()
        if module not in self.ALLOWED_MODULES:
            return self._error(
                f"Módulo '{module}' no soportado. "
                f"Permitidos: {', '.join(sorted(self.ALLOWED_MODULES))}"
            )

        rel_dir, files = self.ALLOWED_MODULES[module]
        root = Path(getattr(Config, "TARGET_PROJECT_ROOT", Path.cwd())).resolve()
        target_dir = (root / rel_dir).resolve()

        try:
            target_dir.relative_to(root)
        except ValueError:
            return self._error(f"Ruta fuera de proyecto: {target_dir}")

        created: list[str] = []
        target_dir.mkdir(parents=True, exist_ok=True)

        for filename in files:
            path = target_dir / filename
            if path.exists():
                continue
            path.write_text(self._file_content(module, filename), encoding="utf-8")
            created.append(str(path.relative_to(root)))

        locale = str(params.get("locale") or "").strip().upper() or None
        created.extend(self._scaffold_adapters(root, module, locale))

        return {
            "ok": True,
            "result": {
                "type": "module_scaffold",
                "module": module,
                "path": rel_dir,
                "created": created,
                "locale": locale,
            },
            "error": None,
        }

    def _scaffold_adapters(
        self,
        root: Path,
        module: str,
        locale: str | None,
    ) -> list[str]:
        if not locale or module not in {"payments", "invoicing"}:
            return []

        created: list[str] = []
        base = root / "src" / "adapters" / locale.lower()
        base.mkdir(parents=True, exist_ok=True)

        init = base / "__init__.py"
        if not init.exists():
            init.write_text(f'"""Adapters locale {locale}."""\n', encoding="utf-8")
            created.append(str(init.relative_to(root)))

        mapping = self.PAYMENT_ADAPTERS if module == "payments" else self.INVOICE_ADAPTERS
        entry = mapping.get(locale)
        if not entry:
            return created

        filename, class_name = entry
        path = base / filename
        if path.exists():
            return created

        protocol = "PaymentProvider" if module == "payments" else "ElectronicInvoiceProvider"
        path.write_text(
            (
                f'"""Adapter {class_name} ({locale}) — stub."""\n'
                "from __future__ import annotations\n\n"
                "from typing import Any\n\n\n"
                f"class {class_name}:\n"
                f'    """Implementa {protocol} para {locale}. Stub sin SDK."""\n\n'
                "    def list_methods(self, locale: str) -> list[dict[str, Any]]:\n"
                "        return []\n\n"
                "    def charge(\n"
                "        self,\n"
                "        amount: float,\n"
                "        currency: str,\n"
                "        method: str,\n"
                "        metadata: dict[str, Any] | None = None,\n"
                "    ) -> dict[str, Any]:\n"
                '        raise NotImplementedError("Conectar SDK real")\n\n'
                "    def refund(\n"
                "        self,\n"
                "        payment_id: str,\n"
                "        amount: float | None = None,\n"
                "    ) -> dict[str, Any]:\n"
                '        raise NotImplementedError("Conectar SDK real")\n\n'
                "    def issue(\n"
                "        self,\n"
                "        ticket: dict[str, Any],\n"
                "        customer: dict[str, Any] | None,\n"
                "        locale: str,\n"
                "    ) -> dict[str, Any]:\n"
                '        raise NotImplementedError("Conectar API fiscal")\n\n'
                "    def cancel(self, invoice_id: str, reason: str) -> dict[str, Any]:\n"
                '        raise NotImplementedError("Conectar API fiscal")\n\n'
                "    def status(self, invoice_id: str) -> dict[str, Any]:\n"
                '        raise NotImplementedError("Conectar API fiscal")\n'
            ),
            encoding="utf-8",
        )
        created.append(str(path.relative_to(root)))
        return created

    def _file_content(self, module: str, filename: str) -> str:
        if filename == "provider.py" and module in self.INTERFACE_STUBS:
            return self.INTERFACE_STUBS[module]
        if filename == "__init__.py":
            return f'"""Módulo {module}."""\n'
        if filename == "service.py":
            return (
                f'"""Servicio de dominio: {module}."""\n'
                "from __future__ import annotations\n\n"
                f"class {self._to_class(module)}Service:\n"
                "    def __init__(self) -> None:\n"
                "        pass\n"
            )
        if filename == "routes.py":
            return (
                f'"""Rutas HTTP del módulo {module}."""\n'
                "from __future__ import annotations\n\n"
                "# Registrar endpoints en el router de la app.\n"
            )
        return f"# {module}/{filename}\n"

    @staticmethod
    def _to_class(module: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", " ", module).title().replace(" ", "")

    def _error(self, message: str) -> dict[str, Any]:
        return {"ok": False, "result": None, "error": message}
