from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.config import Config
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from skills.base import Skill


class ScaffoldModuleSkill(Skill):
    name = "scaffold_module"
    description = "Scaffold de módulo de producto (auth, pos, payments, dental, ...)."
    version = "2.0"
    capabilities = (
        "module_scaffold",
        "pos_module",
        "project_structure",
    )

    ALLOWED_MODULES: dict[str, tuple[str, tuple[str, ...]]] = {
        "auth": ("src/modules/auth", ("__init__.py", "service.py", "routes.py")),
        "pos": ("src/modules/pos", ("__init__.py", "service.py", "routes.py")),
        "catalog": ("src/modules/catalog", ("__init__.py", "service.py", "routes.py")),
        "cash": ("src/modules/cash", ("__init__.py", "service.py", "routes.py")),
        "payments": (
            "src/modules/payments",
            ("__init__.py", "provider.py", "service.py", "factory.py"),
        ),
        "invoicing": (
            "src/modules/invoicing",
            ("__init__.py", "provider.py", "service.py", "factory.py"),
        ),
        "delivery": ("src/modules/delivery", ("__init__.py", "service.py")),
        "reports": ("src/modules/reports", ("__init__.py", "service.py")),
        # dental
        "patients": ("src/modules/patients", ("__init__.py", "service.py", "routes.py")),
        "agenda": ("src/modules/agenda", ("__init__.py", "service.py", "routes.py")),
        "odontogram": (
            "src/modules/odontogram",
            ("__init__.py", "service.py", "models.py"),
        ),
        "clinical_history": ("src/modules/clinical_history", ("__init__.py", "service.py")),
        "prescriptions": ("src/modules/prescriptions", ("__init__.py", "service.py")),
        "inventory": ("src/modules/inventory", ("__init__.py", "service.py")),
        # restaurant
        "reservations": ("src/modules/reservations", ("__init__.py", "service.py")),
        "dashboard": ("src/modules/dashboard", ("__init__.py", "service.py")),
        "sales": ("src/modules/sales", ("__init__.py", "service.py")),
        "tasks": ("src/modules/tasks", ("__init__.py", "service.py")),
    }

    INTERFACE_STUBS = {
        "payments": '''"""Contrato PaymentProvider."""
from __future__ import annotations

from typing import Any, Protocol


class PaymentProvider(Protocol):
    def list_methods(self, locale: str) -> list[dict[str, Any]]: ...

    def charge(
        self,
        amount: float,
        currency: str,
        method: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def refund(
        self,
        payment_id: str,
        amount: float | None = None,
    ) -> dict[str, Any]: ...
''',
        "invoicing": '''"""Contrato ElectronicInvoiceProvider."""
from __future__ import annotations

from typing import Any, Protocol


class ElectronicInvoiceProvider(Protocol):
    def issue(
        self,
        ticket: dict[str, Any],
        customer: dict[str, Any] | None,
        locale: str,
    ) -> dict[str, Any]: ...

    def cancel(self, invoice_id: str, reason: str) -> dict[str, Any]: ...

    def status(self, invoice_id: str) -> dict[str, Any]: ...
''',
    }

    LOCALE_ADAPTERS: dict[str, dict[str, tuple[str, str]]] = {
        "AR": {
            "payments": ("mercadopago.py", "MercadoPagoProvider"),
            "invoicing": ("afip.py", "AfipInvoiceProvider"),
        },
        "MX": {
            "payments": ("mercadopago.py", "MercadoPagoProvider"),
            "invoicing": ("cfdi.py", "CfdiInvoiceProvider"),
        },
        "PE": {
            "payments": ("yape_plin.py", "YapePlinProvider"),
            "invoicing": ("boleta_local.py", "BoletaLocalProvider"),
        },
        "ES": {
            "payments": ("redsys.py", "RedsysProvider"),
            "invoicing": ("verifactu.py", "VerifactuInvoiceProvider"),
        },
        "CL": {
            "payments": ("webpay.py", "WebpayProvider"),
            "invoicing": ("sii_dte.py", "SiiDteProvider"),
        },
        "CO": {
            "payments": ("mercado_pago.py", "MercadoPagoProvider"),
            "invoicing": ("dian.py", "DianInvoiceProvider"),
        },
    }

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        params = dict(step.params or {})
        module = str(params.get("module") or "").strip().lower()
        locale = str(params.get("locale") or plan.metadata.get("locale") or "").strip().upper()

        if module not in self.ALLOWED_MODULES:
            return self._error(f"Módulo no permitido: {module}")

        root = Path(Config.TARGET_PROJECT_ROOT).expanduser().resolve()
        rel_dir, files = self.ALLOWED_MODULES[module]
        mod_dir = root / rel_dir
        mod_dir.mkdir(parents=True, exist_ok=True)

        created: list[str] = []
        for filename in files:
            path = mod_dir / filename
            if path.exists():
                continue
            path.write_text(self._file_content(module, filename), encoding="utf-8")
            created.append(str(path.relative_to(root)))

        adapters_created: list[str] = []
        if module in {"payments", "invoicing"} and locale:
            adapters_created = self._scaffold_adapters(root, module, locale)

        # Facades idempotentes
        created.extend(self._ensure_facades(root, module))

        return {
            "ok": True,
            "result": {
                "type": "module_scaffold",
                "module": module,
                "path": rel_dir,
                "created": created + adapters_created,
                "locale": locale or None,
            },
            "error": None,
        }

    def _ensure_facades(self, root: Path, module: str) -> list[str]:
        created: list[str] = []

        if module == "pos":
            facade = root / "src/modules/pos/sale_facade.py"
            if not facade.exists():
                facade.write_text(self._sale_facade_source(), encoding="utf-8")
                created.append(str(facade.relative_to(root)))

        if module in {"odontogram", "patients", "agenda"}:
            clinical_dir = root / "src/modules/clinical"
            clinical_dir.mkdir(parents=True, exist_ok=True)
            init = clinical_dir / "__init__.py"
            if not init.exists():
                init.write_text('"""Paquete clínica (facades)."""\n', encoding="utf-8")
                created.append(str(init.relative_to(root)))
            facade = clinical_dir / "session_facade.py"
            if not facade.exists():
                facade.write_text(self._clinical_facade_source(), encoding="utf-8")
                created.append(str(facade.relative_to(root)))

        if module in {"dashboard", "reservations", "sales", "tasks"}:
            resto_dir = root / "src/modules/restaurant"
            resto_dir.mkdir(parents=True, exist_ok=True)
            init = resto_dir / "__init__.py"
            if not init.exists():
                init.write_text('"""Paquete restaurant (facades)."""\n', encoding="utf-8")
                created.append(str(init.relative_to(root)))
            facade = resto_dir / "dashboard_facade.py"
            if not facade.exists():
                facade.write_text(self._dashboard_facade_source(), encoding="utf-8")
                created.append(str(facade.relative_to(root)))

        return created

    def _file_content(self, module: str, filename: str) -> str:
        if filename == "provider.py" and module in self.INTERFACE_STUBS:
            return self.INTERFACE_STUBS[module]
        if filename == "__init__.py":
            return f'"""Módulo {module}."""\n'
        if filename == "factory.py":
            if module == "payments":
                return self._payments_factory_source()
            if module == "invoicing":
                return self._invoicing_factory_source()
        if filename == "models.py" and module == "odontogram":
            return self._odontogram_models_source()
        if filename == "service.py":
            generators = {
                "payments": self._payments_service_source,
                "invoicing": self._invoicing_service_source,
                "catalog": self._catalog_service_source,
                "pos": self._pos_service_source,
                "cash": self._cash_service_source,
                "auth": self._auth_service_source,
                "patients": self._patients_service_source,
                "odontogram": self._odontogram_service_source,
                "agenda": self._agenda_service_source,
            }
            if module in generators:
                return generators[module]()
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

    def _scaffold_adapters(
        self,
        root: Path,
        module: str,
        locale: str,
    ) -> list[str]:
        spec = self.LOCALE_ADAPTERS.get(locale)
        if not spec or module not in spec:
            return []
        filename, classname = spec[module]
        adapter_dir = root / "src" / "adapters" / locale.lower()
        adapter_dir.mkdir(parents=True, exist_ok=True)
        created: list[str] = []

        init = adapter_dir / "__init__.py"
        if not init.exists():
            init.write_text(f'"""Adapters locale={locale}."""\n', encoding="utf-8")
            created.append(str(init.relative_to(root)))

        path = adapter_dir / filename
        if not path.exists():
            if module == "payments":
                body = self._payment_adapter_stub(classname, locale)
            else:
                body = self._invoice_adapter_stub(classname, locale)
            path.write_text(body, encoding="utf-8")
            created.append(str(path.relative_to(root)))
        return created

    @staticmethod
    def _payment_adapter_stub(classname: str, locale: str) -> str:
        return f'''"""Adapter de pagos {classname} ({locale}). Stub sin SDK real."""
from __future__ import annotations

from typing import Any


class {classname}:
    def list_methods(self, locale: str) -> list[dict[str, Any]]:
        return [
            {{"id": "card", "name": "Tarjeta"}},
            {{"id": "efectivo", "name": "Efectivo"}},
        ]

    def charge(
        self,
        amount: float,
        currency: str,
        method: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError(
            "Conectar SDK de pagos ({classname})"
        )

    def refund(
        self,
        payment_id: str,
        amount: float | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError("Conectar refund en {classname}")
'''

    @staticmethod
    def _invoice_adapter_stub(classname: str, locale: str) -> str:
        return f'''"""Adapter de facturación {classname} ({locale}). Stub sin API fiscal real."""
from __future__ import annotations

from typing import Any


class {classname}:
    def issue(
        self,
        ticket: dict[str, Any],
        customer: dict[str, Any] | None,
        locale: str,
    ) -> dict[str, Any]:
        raise NotImplementedError("Conectar API fiscal {classname}")

    def cancel(self, invoice_id: str, reason: str) -> dict[str, Any]:
        raise NotImplementedError("Conectar cancelación en {classname}")

    def status(self, invoice_id: str) -> dict[str, Any]:
        raise NotImplementedError("Conectar status en {classname}")
'''

    def _payments_service_source(self) -> str:
        return '''"""Servicio de dominio: payments."""
from __future__ import annotations

from typing import Any

from src.modules.payments.provider import PaymentProvider


class MockPaymentProvider:
    def list_methods(self, locale: str) -> list[dict[str, Any]]:
        return [
            {"id": "efectivo", "name": "Efectivo"},
            {"id": "card", "name": "Tarjeta"},
        ]

    def charge(
        self,
        amount: float,
        currency: str,
        method: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        key = (metadata or {}).get("idempotency_key")
        pid = f"mock-{method}-{amount}"
        if key:
            pid = f"mock-{key}"
        return {
            "ok": True,
            "payment_id": pid,
            "amount": amount,
            "currency": currency,
            "method": method,
            "status": "approved",
            "metadata": metadata or {},
        }

    def refund(
        self,
        payment_id: str,
        amount: float | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "payment_id": payment_id,
            "refunded": amount,
            "status": "refunded",
        }


class PaymentsService:
    def __init__(self, provider: PaymentProvider | None = None) -> None:
        self.provider: PaymentProvider = provider or MockPaymentProvider()

    def available_methods(self, locale: str) -> list[dict[str, Any]]:
        return self.provider.list_methods(locale)

    def charge(
        self,
        amount: float,
        currency: str,
        method: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.provider.charge(amount, currency, method, metadata)

    def refund(self, payment_id: str, amount: float | None = None) -> dict[str, Any]:
        return self.provider.refund(payment_id, amount)
'''

    def _invoicing_service_source(self) -> str:
        return '''"""Servicio de dominio: invoicing."""
from __future__ import annotations

from typing import Any

from src.modules.invoicing.provider import ElectronicInvoiceProvider


class MockInvoiceProvider:
    def issue(
        self,
        ticket: dict[str, Any],
        customer: dict[str, Any] | None,
        locale: str,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "invoice_id": f"mock-inv-{locale}",
            "fiscal_id": "MOCK-CAE-000",
            "ticket": ticket,
            "customer": customer,
            "locale": locale,
            "status": "issued",
        }

    def cancel(self, invoice_id: str, reason: str) -> dict[str, Any]:
        return {
            "ok": True,
            "invoice_id": invoice_id,
            "reason": reason,
            "status": "cancelled",
        }

    def status(self, invoice_id: str) -> dict[str, Any]:
        return {"ok": True, "invoice_id": invoice_id, "status": "issued"}


class InvoicingService:
    def __init__(self, provider: ElectronicInvoiceProvider | None = None) -> None:
        self.provider: ElectronicInvoiceProvider = provider or MockInvoiceProvider()

    def issue(
        self,
        ticket: dict[str, Any],
        customer: dict[str, Any] | None = None,
        locale: str = "AR",
    ) -> dict[str, Any]:
        return self.provider.issue(ticket, customer, locale)

    def cancel(self, invoice_id: str, reason: str = "") -> dict[str, Any]:
        return self.provider.cancel(invoice_id, reason)

    def status(self, invoice_id: str) -> dict[str, Any]:
        return self.provider.status(invoice_id)
'''

    def _payments_factory_source(self) -> str:
        return '''"""Selección de PaymentProvider según locale / config."""
from __future__ import annotations

from src.modules.payments.provider import PaymentProvider
from src.modules.payments.service import MockPaymentProvider


def get_payment_provider(
    locale: str,
    *,
    use_mock: bool = True,
) -> PaymentProvider:
    code = (locale or "").strip().upper()
    if use_mock:
        return MockPaymentProvider()
    if code == "AR":
        from src.adapters.ar.mercadopago import MercadoPagoProvider
        return MercadoPagoProvider()
    if code == "MX":
        from src.adapters.mx.mercadopago import MercadoPagoProvider
        return MercadoPagoProvider()
    if code == "PE":
        from src.adapters.pe.yape_plin import YapePlinProvider
        return YapePlinProvider()
    if code == "ES":
        from src.adapters.es.redsys import RedsysProvider
        return RedsysProvider()
    if code == "CL":
        from src.adapters.cl.webpay import WebpayProvider
        return WebpayProvider()
    if code == "CO":
        from src.adapters.co.mercado_pago import MercadoPagoProvider
        return MercadoPagoProvider()
    return MockPaymentProvider()
'''

    def _invoicing_factory_source(self) -> str:
        return '''"""Selección de ElectronicInvoiceProvider según locale / config."""
from __future__ import annotations

from src.modules.invoicing.provider import ElectronicInvoiceProvider
from src.modules.invoicing.service import MockInvoiceProvider


def get_invoice_provider(
    locale: str,
    *,
    use_mock: bool = True,
) -> ElectronicInvoiceProvider:
    code = (locale or "").strip().upper()
    if use_mock:
        return MockInvoiceProvider()
    if code == "AR":
        from src.adapters.ar.afip import AfipInvoiceProvider
        return AfipInvoiceProvider()
    if code == "MX":
        from src.adapters.mx.cfdi import CfdiInvoiceProvider
        return CfdiInvoiceProvider()
    if code == "PE":
        from src.adapters.pe.boleta_local import BoletaLocalProvider
        return BoletaLocalProvider()
    if code == "ES":
        from src.adapters.es.verifactu import VerifactuInvoiceProvider
        return VerifactuInvoiceProvider()
    if code == "CL":
        from src.adapters.cl.sii_dte import SiiDteProvider
        return SiiDteProvider()
    if code == "CO":
        from src.adapters.co.dian import DianInvoiceProvider
        return DianInvoiceProvider()
    return MockInvoiceProvider()
'''

    def _catalog_service_source(self) -> str:
        return '''"""Catálogo de productos en memoria."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Producto:
    sku: str
    nombre: str
    precio: float
    activo: bool = True


class CatalogService:
    def __init__(self) -> None:
        self._items: dict[str, Producto] = {}

    def add(self, producto: Producto) -> None:
        self._items[producto.sku] = producto

    def update(
        self,
        sku: str,
        nombre: str | None = None,
        precio: float | None = None,
        activo: bool | None = None,
    ) -> None:
        p = self._items.get(sku)
        if not p:
            raise ValueError(f"Producto {sku} no encontrado")
        if nombre is not None:
            p.nombre = nombre
        if precio is not None:
            p.precio = precio
        if activo is not None:
            p.activo = activo

    def get(self, sku: str) -> Producto | None:
        return self._items.get(sku)

    def list(self) -> list[Producto]:
        return list(self._items.values())

    def deactivate(self, sku: str) -> None:
        self.update(sku, activo=False)
'''

    def _pos_service_source(self) -> str:
        return '''"""POS: pedidos en memoria, líneas resueltas desde catálogo."""
from __future__ import annotations

from typing import Any

from src.modules.catalog.service import CatalogService


class PosService:
    def __init__(self, catalog: CatalogService | None = None) -> None:
        self.catalog = catalog or CatalogService()
        self.pedidos: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(self, pedido_id: int | None = None) -> int:
        pid = pedido_id if pedido_id is not None else self._next_id
        if pedido_id is None:
            self._next_id += 1
        self.pedidos[pid] = {
            "lineas": [],
            "total": 0.0,
            "forma_pago": None,
            "estado": "abierto",
        }
        return pid

    def add_line_from_catalog(self, pedido_id: int, sku: str, qty: int) -> None:
        p = self.pedidos.get(pedido_id)
        if not p:
            raise ValueError("Pedido no encontrado")
        prod = self.catalog.get(sku)
        if not prod or not prod.activo:
            raise ValueError(f"SKU no disponible: {sku}")
        line = {
            "sku": sku,
            "nombre": prod.nombre,
            "precio": prod.precio,
            "cantidad": qty,
            "subtotal": prod.precio * qty,
        }
        p["lineas"].append(line)
        p["total"] = float(sum(x["subtotal"] for x in p["lineas"]))

    def pay(self, pedido_id: int, forma_pago: str) -> None:
        p = self.pedidos.get(pedido_id)
        if not p:
            raise ValueError("Pedido no encontrado")
        p["forma_pago"] = forma_pago
        p["estado"] = "pagado"

    def close(self, pedido_id: int) -> None:
        p = self.pedidos.get(pedido_id)
        if not p:
            raise ValueError("Pedido no encontrado")
        p["estado"] = "cerrado"
'''

    def _cash_service_source(self) -> str:
        return '''"""Caja en memoria."""
from __future__ import annotations

from typing import Any


class CashService:
    def __init__(self) -> None:
        self._open = False
        self._saldo = 0.0
        self._movimientos: list[dict[str, Any]] = []

    def open_cash_box(self, initial_amount: float) -> None:
        self._open = True
        self._saldo = float(initial_amount)
        self._movimientos = []

    def close_cash_box(self) -> None:
        self._open = False
        self._saldo = 0.0
        self._movimientos = []

    def add_movement(self, amount: float, description: str) -> None:
        if not self._open:
            raise ValueError("La caja no está abierta")
        self._saldo += float(amount)
        self._movimientos.append(
            {"monto": float(amount), "descripcion": description}
        )

    def get_balance(self) -> float:
        return self._saldo if self._open else 0.0

    def get_movements(self) -> list[dict[str, Any]]:
        return list(self._movimientos)
'''

    def _auth_service_source(self) -> str:
        return '''"""Auth simple en memoria."""
from __future__ import annotations

import hashlib


class User:
    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password_hash = self._hash(password)

    @staticmethod
    def _hash(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == self._hash(password)


class AuthService:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self._sessions: set[str] = set()

    def register(self, email: str, password: str) -> bool:
        if email in self.users:
            return False
        self.users[email] = User(email, password)
        return True

    def login(self, email: str, password: str) -> bool:
        user = self.users.get(email)
        if not user or not user.check_password(password):
            return False
        self._sessions.add(email)
        return True

    def logout(self, email: str) -> bool:
        if email in self._sessions:
            self._sessions.discard(email)
            return True
        return False
'''

    def _patients_service_source(self) -> str:
        return '''"""Pacientes en memoria."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Patient:
    id: str
    nombre: str
    documento: str = ""
    telefono: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class PatientsService:
    def __init__(self) -> None:
        self._items: dict[str, Patient] = {}

    def add(self, patient: Patient) -> None:
        self._items[patient.id] = patient

    def get(self, patient_id: str) -> Patient | None:
        return self._items.get(patient_id)

    def list(self) -> list[Patient]:
        return list(self._items.values())
'''

    def _odontogram_models_source(self) -> str:
        return '''"""Hallazgos y piezas del odontograma."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Surface(str, Enum):
    VESTIBULAR = "V"
    LINGUAL = "L"
    MESIAL = "M"
    DISTAL = "D"
    OCLUSAL = "O"


class FindingType(str, Enum):
    SANO = "sano"
    CARIES = "caries"
    OBTURACION = "obturacion"
    CORONA = "corona"
    AUSENTE = "ausente"
    IMPLANTE = "implante"


@dataclass
class Finding:
    surface: Surface
    kind: FindingType
    note: str = ""


@dataclass
class Tooth:
    number: int
    findings: list[Finding] = field(default_factory=list)
'''

    def _odontogram_service_source(self) -> str:
        return '''"""Odontograma en memoria por paciente."""
from __future__ import annotations

from src.modules.odontogram.models import Finding, FindingType, Surface, Tooth


class OdontogramService:
    def __init__(self) -> None:
        self._charts: dict[str, dict[int, Tooth]] = {}

    def ensure_patient(self, patient_id: str) -> None:
        if patient_id not in self._charts:
            teeth = {}
            for n in (
                list(range(11, 19))
                + list(range(21, 29))
                + list(range(31, 39))
                + list(range(41, 49))
            ):
                teeth[n] = Tooth(number=n)
            self._charts[patient_id] = teeth

    def add_finding(
        self,
        patient_id: str,
        tooth: int,
        surface: Surface,
        kind: FindingType,
        note: str = "",
    ) -> None:
        self.ensure_patient(patient_id)
        t = self._charts[patient_id].get(tooth)
        if not t:
            raise ValueError(f"Pieza inválida: {tooth}")
        t.findings.append(Finding(surface=surface, kind=kind, note=note))

    def get_tooth(self, patient_id: str, tooth: int) -> Tooth | None:
        self.ensure_patient(patient_id)
        return self._charts.get(patient_id, {}).get(tooth)

    def summary(self, patient_id: str) -> dict[str, int]:
        self.ensure_patient(patient_id)
        counts: dict[str, int] = {}
        for t in self._charts[patient_id].values():
            for f in t.findings:
                counts[f.kind.value] = counts.get(f.kind.value, 0) + 1
        return counts
'''

    def _agenda_service_source(self) -> str:
        return '''"""Agenda de turnos en memoria."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Appointment:
    id: str
    patient_id: str
    starts_at: str
    status: str = "scheduled"
    note: str = ""


class AgendaService:
    def __init__(self) -> None:
        self._items: dict[str, Appointment] = {}

    def schedule(self, appt: Appointment) -> None:
        self._items[appt.id] = appt

    def list_for_patient(self, patient_id: str) -> list[Appointment]:
        return [a for a in self._items.values() if a.patient_id == patient_id]

    def set_status(self, appt_id: str, status: str) -> None:
        a = self._items.get(appt_id)
        if not a:
            raise ValueError("Turno no encontrado")
        a.status = status
'''

    def _sale_facade_source(self) -> str:
        return '''"""Fachada de venta en memoria (demo POS)."""
from __future__ import annotations

from typing import Any

from src.modules.catalog.service import CatalogService, Producto
from src.modules.pos.service import PosService
from src.modules.cash.service import CashService
from src.modules.payments.factory import get_payment_provider
from src.modules.payments.service import PaymentsService
from src.modules.invoicing.factory import get_invoice_provider
from src.modules.invoicing.service import InvoicingService


class SaleFacade:
    def __init__(self, locale: str = "AR", use_mock: bool = True) -> None:
        self.locale = (locale or "AR").upper()
        self.catalog = CatalogService()
        self.pos = PosService(self.catalog)
        self.cash = CashService()
        self.payments = PaymentsService(
            get_payment_provider(self.locale, use_mock=use_mock)
        )
        self.invoicing = InvoicingService(
            get_invoice_provider(self.locale, use_mock=use_mock)
        )
        self.cash.open_cash_box(100.0)

    def seed_product(self, sku: str, nombre: str, precio: float) -> None:
        self.catalog.add(Producto(sku, nombre, precio))

    def sell(
        self,
        lines: list[tuple[str, int]],
        method: str = "efectivo",
    ) -> dict[str, Any]:
        pid = self.pos.create()
        for sku, qty in lines:
            self.pos.add_line_from_catalog(pid, sku, qty)
        total = float(self.pos.pedidos[pid].get("total") or 0)
        self.pos.pay(pid, method)
        payment = self.payments.charge(
            total,
            self._currency(),
            method,
            metadata={"idempotency_key": f"ticket:{pid}:pay:1"},
        )
        if payment.get("ok"):
            self.cash.add_movement(total, f"venta {pid}")
        invoice = self.invoicing.issue(
            {"pedido_id": pid, "total": total, "lines": lines},
            None,
            self.locale,
        )
        self.pos.close(pid)
        return {
            "ok": bool(payment.get("ok")),
            "total": total,
            "payment": payment,
            "invoice": invoice,
            "cash_balance": self.cash.get_balance(),
            "estado": self.pos.pedidos.get(pid, {}).get("estado"),
            "pedido_id": pid,
        }

    def _currency(self) -> str:
        return {
            "AR": "ARS",
            "MX": "MXN",
            "PE": "PEN",
            "ES": "EUR",
            "CL": "CLP",
            "CO": "COP",
        }.get(self.locale, "USD")
'''

    def _clinical_facade_source(self) -> str:
        return '''"""Fachada de sesión clínica en memoria (demo dental)."""
from __future__ import annotations

from typing import Any

from src.modules.patients.service import Patient, PatientsService
from src.modules.agenda.service import Appointment, AgendaService
from src.modules.odontogram.service import OdontogramService
from src.modules.odontogram.models import FindingType, Surface

try:
    from src.modules.payments.factory import get_payment_provider
    from src.modules.payments.service import PaymentsService
except ImportError:
    PaymentsService = None  # type: ignore
    get_payment_provider = None  # type: ignore


class ClinicalSessionFacade:
    def __init__(self, locale: str = "AR", use_mock: bool = True) -> None:
        self.locale = (locale or "AR").upper()
        self.patients = PatientsService()
        self.agenda = AgendaService()
        self.odontogram = OdontogramService()
        self.payments = None
        if PaymentsService and get_payment_provider:
            self.payments = PaymentsService(
                get_payment_provider(self.locale, use_mock=use_mock)
            )

    def seed_patient(
        self,
        patient_id: str,
        nombre: str,
        documento: str = "",
        telefono: str = "",
    ) -> None:
        self.patients.add(
            Patient(
                id=patient_id,
                nombre=nombre,
                documento=documento,
                telefono=telefono,
            )
        )
        self.odontogram.ensure_patient(patient_id)

    def schedule(
        self,
        appt_id: str,
        patient_id: str,
        starts_at: str,
        note: str = "",
    ) -> None:
        if not self.patients.get(patient_id):
            raise ValueError(f"Paciente inexistente: {patient_id}")
        self.agenda.schedule(
            Appointment(
                id=appt_id,
                patient_id=patient_id,
                starts_at=starts_at,
                note=note,
            )
        )

    def record_finding(
        self,
        patient_id: str,
        tooth: int,
        surface: str,
        kind: str,
        note: str = "",
    ) -> None:
        surf = Surface(surface) if not isinstance(surface, Surface) else surface
        k = FindingType(kind) if not isinstance(kind, FindingType) else kind
        self.odontogram.add_finding(patient_id, tooth, surf, k, note)

    def complete_appointment(self, appt_id: str) -> None:
        self.agenda.set_status(appt_id, "done")

    def charge_consultation(
        self,
        amount: float,
        method: str = "efectivo",
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not self.payments:
            return {
                "ok": True,
                "status": "skipped",
                "reason": "payments no disponible",
            }
        currency = {
            "AR": "ARS",
            "MX": "MXN",
            "PE": "PEN",
            "ES": "EUR",
            "CL": "CLP",
            "CO": "COP",
        }.get(self.locale, "USD")
        meta = {}
        if idempotency_key:
            meta["idempotency_key"] = idempotency_key
        return self.payments.charge(amount, currency, method, metadata=meta or None)

    def run_demo_session(
        self,
        patient_id: str = "p1",
        nombre: str = "Jorge Martínez",
    ) -> dict[str, Any]:
        self.seed_patient(patient_id, nombre, documento="20111222")
        self.schedule("a1", patient_id, "2026-08-24T10:30:00", note="Control")
        self.record_finding(patient_id, 16, "O", "caries", "mancha occlusal")
        self.record_finding(patient_id, 16, "V", "obturacion", "")
        self.complete_appointment("a1")
        payment = self.charge_consultation(
            25_000.0,
            "efectivo",
            idempotency_key=f"consult:{patient_id}:a1",
        )
        return {
            "ok": True,
            "patient": self.patients.get(patient_id),
            "odontogram_summary": self.odontogram.summary(patient_id),
            "tooth_16": self.odontogram.get_tooth(patient_id, 16),
            "appointments": self.agenda.list_for_patient(patient_id),
            "payment": payment,
        }
'''

    def _dashboard_facade_source(self) -> str:
        return '''"""Fachada de panel restaurant en memoria (demo)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Reservation:
    id: str
    time: str
    table: str
    guest: str
    pax: int
    status: str = "confirmed"


@dataclass
class TaskItem:
    id: str
    title: str
    priority: str = "media"
    done: bool = False


@dataclass
class SaleLine:
    product: str
    category: str
    amount: float
    qty: int = 1


@dataclass
class DashboardState:
    reservations: list[Reservation] = field(default_factory=list)
    tasks: list[TaskItem] = field(default_factory=list)
    sales: list[SaleLine] = field(default_factory=list)


class DashboardFacade:
    def __init__(self, locale: str = "AR") -> None:
        self.locale = (locale or "AR").upper()
        self.state = DashboardState()

    def seed_demo(self) -> None:
        self.state.reservations = [
            Reservation("r1", "20:00", "Mesa 4", "Ana", 4),
            Reservation("r2", "20:30", "Mesa 12", "Luis", 2),
            Reservation("r3", "21:00", "Mesa 7", "Sofía", 6),
        ]
        self.state.tasks = [
            TaskItem("t1", "Reponer barra", "alta"),
            TaskItem("t2", "Cierre de caja mediodía", "media"),
            TaskItem("t3", "Briefing cocina", "media"),
            TaskItem("t4", "Actualizar menú QR", "baja"),
            TaskItem("t5", "Pedido a proveedor", "alta"),
        ]
        self.state.sales = [
            SaleLine("Burger", "comidas", 12_000, 30),
            SaleLine("Pizza", "comidas", 15_000, 22),
            SaleLine("Ensalada", "comidas", 8_000, 18),
            SaleLine("Café", "bebidas", 2_500, 40),
            SaleLine("Brownie", "postres", 3_500, 15),
            SaleLine("Gaseosa", "bebidas", 2_000, 35),
            SaleLine("Vino", "bebidas", 9_000, 8),
        ]

    def total_sales(self) -> float:
        return float(sum(s.amount * s.qty for s in self.state.sales))

    def ticket_count(self) -> int:
        return int(sum(s.qty for s in self.state.sales))

    def average_ticket(self) -> float:
        n = self.ticket_count()
        return self.total_sales() / n if n else 0.0

    def sales_by_category(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for s in self.state.sales:
            out[s.category] = out.get(s.category, 0.0) + s.amount * s.qty
        return out

    def top_products(self, limit: int = 5) -> list[dict[str, Any]]:
        agg: dict[str, float] = {}
        for s in self.state.sales:
            agg[s.product] = agg.get(s.product, 0.0) + s.amount * s.qty
        ranked = sorted(agg.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"product": n, "total": t} for n, t in ranked]

    def pending_tasks(self) -> list[TaskItem]:
        return [t for t in self.state.tasks if not t.done]

    def snapshot(self) -> dict[str, Any]:
        if not self.state.sales and not self.state.reservations:
            self.seed_demo()
        return {
            "ok": True,
            "locale": self.locale,
            "kpis": {
                "ventas": self.total_sales(),
                "reservas": len(self.state.reservations),
                "ticket_promedio": round(self.average_ticket(), 2),
                "tareas_pendientes": len(self.pending_tasks()),
            },
            "reservations": [
                {
                    "id": r.id,
                    "time": r.time,
                    "table": r.table,
                    "guest": r.guest,
                    "pax": r.pax,
                    "status": r.status,
                }
                for r in self.state.reservations
            ],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "done": t.done,
                }
                for t in self.pending_tasks()
            ],
            "sales_by_category": self.sales_by_category(),
            "top_products": self.top_products(),
        }
'''

    @staticmethod
    def _to_class(module: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", " ", module).title().replace(" ", "")

    def _error(self, message: str) -> dict[str, Any]:
        return {"ok": False, "result": None, "error": message}
