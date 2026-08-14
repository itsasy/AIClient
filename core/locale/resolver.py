from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from core.config import Config

logger = logging.getLogger(__name__)

try:
    from core.locale.packs import get_locale_pack, locale_summary as pack_summary
except ImportError:

    def get_locale_pack(code: str | None):  # type: ignore
        return None

    def pack_summary(code: str | None) -> str:  # type: ignore
        return ""


class LocaleResolver:
    """
    Resuelve conocimiento de locale para specs/planes.

    Orden de prioridad (segundo cerebro primero):
      1. Obsidian: Locales/{CODE}.md o similar
      2. Engram recall
      3. Seed en código (packs.py) como fallback
    """

    name = "locale_resolver"

    OBSIDIAN_CANDIDATES = (
        "Locales/{code}.md",
        "locales/{code}.md",
        "Locale/{code}.md",
        "POS/Locales/{code}.md",
        "Knowledge/Locales/{code}.md",
    )

    def resolve(
        self,
        code: str | None,
        engram: Any | None = None,
    ) -> dict[str, Any]:
        normalized = (code or "").strip().upper() or None
        sources: list[str] = []
        text_parts: list[str] = []

        if normalized:
            obsidian_text = self._from_obsidian(normalized)
            if obsidian_text:
                sources.append("obsidian")
                text_parts.append(obsidian_text)

            engram_text = self._from_engram(normalized, engram)
            if engram_text:
                sources.append("engram")
                text_parts.append(engram_text)

            pack = get_locale_pack(normalized)
            if pack is not None:
                sources.append("seed")
                text_parts.append(pack_summary(normalized))

        summary = "\n\n".join(p for p in text_parts if p).strip()
        if not summary:
            summary = (
                "Locale no especificado o sin conocimiento cargado. "
                "No asumir país, moneda, pagos ni régimen fiscal."
            )
            sources.append("default")

        logger.info(
            "Locale resolve | code=%s | sources=%s",
            normalized,
            sources,
        )

        return {
            "locale_code": normalized,
            "locale_summary": summary,
            "sources": sources,
        }

    def _obsidian_root(self) -> Path | None:
        for attr in ("OBSIDIAN_VAULT", "OBSIDIAN_VAULT_PATH", "OBSIDIAN_PATH", "OBSIDIAN_DIR"):
            raw = getattr(Config, attr, None)
            if raw:
                path = Path(str(raw)).expanduser()
                if path.is_dir():
                    return path
        return None

    def _from_obsidian(self, code: str) -> str:
        root = self._obsidian_root()
        if root is None:
            return ""

        for pattern in self.OBSIDIAN_CANDIDATES:
            path = root / pattern.format(code=code)
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8").strip()
                    if text:
                        logger.info("Locale %s cargado desde Obsidian: %s", code, path)
                        return f"[Obsidian {path.name}]\n{text[:6000]}"
                except OSError as exc:
                    logger.warning("No se pudo leer %s: %s", path, exc)
        return ""

    def _from_engram(self, code: str, engram: Any | None) -> str:
        if engram is None:
            return ""
        try:
            query = f"locale {code} pagos facturación moneda POS"
            results = engram.recall(query, limit=3)
        except Exception as exc:
            logger.debug("Engram locale recall falló: %s", exc)
            return ""

        chunks: list[str] = []
        for item in results or []:
            if isinstance(item, dict):
                content = str(item.get("content") or item.get("text") or "").strip()
            else:
                content = str(item).strip()
            if content:
                chunks.append(content[:2000])
        if not chunks:
            return ""
        return "[Engram]\n" + "\n---\n".join(chunks)


_resolver = LocaleResolver()


def resolve_locale(code: str | None, engram: Any | None = None) -> dict[str, Any]:
    return _resolver.resolve(code, engram=engram)
