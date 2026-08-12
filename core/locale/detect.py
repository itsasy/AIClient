from __future__ import annotations

import re

_CODE_PATTERNS = (
    r"\bpa[ií]s\s*[=:]\s*([A-Za-z]{2})\b",
    r"\bcountry\s*[=:]\s*([A-Za-z]{2})\b",
    r"\blocale\s*[=:]\s*([A-Za-z]{2})\b",
    r"\b(AR|PE|MX|CL|CO|UY|BR|ES|US|EC|BO|PY)\b",
)

_NAME_TO_CODE = {
    "argentina": "AR",
    "perú": "PE",
    "peru": "PE",
    "méxico": "MX",
    "mexico": "MX",
    "chile": "CL",
    "colombia": "CO",
    "españa": "ES",
    "espana": "ES",
    "spain": "ES",
    "uruguay": "UY",
    "brasil": "BR",
    "brazil": "BR",
    "ecuador": "EC",
    "bolivia": "BO",
    "paraguay": "PY",
    "estados unidos": "US",
    "united states": "US",
}


def detect_locale(text: str | None) -> str | None:
    """
    Detecta código de país/locale en texto libre.
    Retorna ISO-ish de 2 letras o None.
    """
    if not text or not str(text).strip():
        return None

    raw = str(text)
    for pat in _CODE_PATTERNS:
        m = re.search(pat, raw, re.IGNORECASE)
        if m:
            return m.group(1).upper()

    lower = raw.lower()
    # nombres compuestos primero
    for name in sorted(_NAME_TO_CODE.keys(), key=len, reverse=True):
        if name in lower:
            return _NAME_TO_CODE[name]
    return None
