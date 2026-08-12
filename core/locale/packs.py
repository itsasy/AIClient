from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LocalePack:
    """
    Conocimiento regional para specs / planes / scaffolding.

    No implementa pasarelas ni AFIP/CFDI.
    Solo orienta generación y evita hardcode de un solo país.
    """

    code: str
    country: str
    currency: str
    payment_methods: tuple[str, ...]
    invoicing: str
    notes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


PACKS: dict[str, LocalePack] = {
    "PE": LocalePack(
        code="PE",
        country="Perú",
        currency="PEN",
        payment_methods=(
            "efectivo",
            "yape",
            "plin",
            "tarjeta",
            "transferencia_bcp",
            "transferencia_interbank",
        ),
        invoicing="boleta_factura_local",
        notes=(
            "Medios de pago locales frecuentes en retail/food service.",
            "No reutilizar Yape/Plin fuera de PE.",
        ),
    ),
    "AR": LocalePack(
        code="AR",
        country="Argentina",
        currency="ARS",
        payment_methods=(
            "efectivo",
            "mercado_pago",
            "transferencia",
            "qr",
            "tarjeta",
        ),
        invoicing="afip_factura_electronica",
        notes=(
            "Facturación electrónica AFIP (CAE; tipos A/B/C según régimen).",
            "IVA y percepciones dependen del contribuyente.",
        ),
        metadata={
            "invoice_authority": "AFIP",
            "suggested_providers": ("mercado_pago",),
        },
    ),
    "MX": LocalePack(
        code="MX",
        country="México",
        currency="MXN",
        payment_methods=(
            "efectivo",
            "tarjeta",
            "spei",
            "oxxo",
            "mercado_pago",
        ),
        invoicing="cfdi_4_0",
        notes=(
            "Comprobante fiscal digital CFDI 4.0.",
            "Considerar uso de PAC autorizado para timbrado.",
        ),
        metadata={
            "invoice_authority": "SAT",
            "suggested_providers": ("stripe", "mercado_pago", "conekta"),
        },
    ),
    "ES": LocalePack(
        code="ES",
        country="España",
        currency="EUR",
        payment_methods=(
            "efectivo",
            "tarjeta",
            "bizum",
            "transferencia_sepa",
            "redsys",
        ),
        invoicing="factura_ue_verifactu",
        notes=(
            "Cumplir facturación electrónica / VeriFactu según normativa vigente.",
            "IVA UE; valorar OSS si hay ventas cross-border.",
        ),
        metadata={
            "invoice_authority": "AEAT",
            "suggested_providers": ("redsys", "stripe"),
        },
    ),
    "CL": LocalePack(
        code="CL",
        country="Chile",
        currency="CLP",
        payment_methods=(
            "efectivo",
            "tarjeta",
            "transferencia",
            "webpay",
            "mercado_pago",
        ),
        invoicing="dte_sii",
        notes=(
            "Documentos tributarios electrónicos (DTE) ante el SII.",
            "Webpay es habitual en e-commerce/POS integrado.",
        ),
        metadata={
            "invoice_authority": "SII",
            "suggested_providers": ("webpay", "mercado_pago"),
        },
    ),
    "CO": LocalePack(
        code="CO",
        country="Colombia",
        currency="COP",
        payment_methods=(
            "efectivo",
            "tarjeta",
            "pse",
            "nequi",
            "daviplata",
            "mercado_pago",
        ),
        invoicing="factura_electronica_dian",
        notes=(
            "Facturación electrónica DIAN.",
            "PSE y billeteras locales son relevantes en cobros.",
        ),
        metadata={
            "invoice_authority": "DIAN",
            "suggested_providers": ("mercado_pago", "payu"),
        },
    ),
}


def get_locale_pack(code: str | None) -> LocalePack | None:
    if not code:
        return None
    return PACKS.get(str(code).strip().upper())


def list_locale_codes() -> list[str]:
    return sorted(PACKS.keys())


def register_locale_pack(pack: LocalePack) -> None:
    """Permite extender en runtime (plugins, configs de cliente)."""
    PACKS[pack.code.upper()] = pack


def locale_summary(code: str | None) -> str:
    pack = get_locale_pack(code)
    if not pack:
        return (
            "Locale no especificado. " "No asumir país, moneda, medios de pago ni régimen fiscal."
        )
    methods = ", ".join(pack.payment_methods)
    notes = " ".join(pack.notes)
    return (
        f"País={pack.country} ({pack.code}) moneda={pack.currency}. "
        f"Pagos sugeridos: {methods}. "
        f"Facturación: {pack.invoicing}. {notes}"
    )
