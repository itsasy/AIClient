from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.config import Config
from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)

PREFERRED_NAMES = (
    "Arquitectura-de-proyecto.md",
    "Estilo-de-codigo.md",
    "UI-Design-System.md",
    "Pagos-e-idempotencia.md",
    "Pagos-y-facturacion.md",
    "UI-POS-Shell.md",
)

MAX_TOTAL_CHARS = 5500
MAX_FILE_CHARS = 1800


class StandardsProvider(BaseContextProvider):
    """
    Expone standards de diseño/arquitectura al ContextManager.

    Orden de fuentes:
      1. OBSIDIAN_VAULT_PATH/Standards/*.md
      2. (opcional) StandardsLearner list_standards()
    """

    key = "standards"

    def __init__(self) -> None:
        self._learner = None
        try:
            from core.standards_learner import StandardsLearner

            self._learner = StandardsLearner()
        except Exception:
            logger.debug("StandardsLearner no disponible", exc_info=True)

    def provide(self, plan: ExecutionPlan) -> dict[str, Any]:
        """API nueva (si BaseContextProvider usa provide)."""
        return self._build_payload(plan)

    def load(self, plan: ExecutionPlan, context: dict) -> None:
        """API legacy (si el registry llama load)."""
        payload = self._build_payload(plan)
        if payload:
            context[self.key] = payload

    def _build_payload(self, plan: ExecutionPlan) -> dict[str, Any]:
        notes = self._load_vault_standards()
        learned: list[Any] = []
        if self._learner is not None:
            try:
                learned = list(self._learner.list_standards() or [])
            except Exception:
                logger.debug("list_standards falló", exc_info=True)

        if not notes and not learned:
            logger.warning("StandardsProvider: sin notas en vault ni learned_standards")
            return {
                "summary": (
                    "Standards no cargados. Respetar contratos genéricos: "
                    "no inventar stack; pagos/fisco vía adapters; UI design system."
                ),
                "sources": [],
            }

        text_blocks: list[str] = []
        sources: list[str] = []
        used = 0
        for name, body in notes:
            chunk = body.strip()
            if not chunk:
                continue
            if len(chunk) > MAX_FILE_CHARS:
                chunk = chunk[: MAX_FILE_CHARS - 20] + "\n[...truncado]"
            if used + len(chunk) > MAX_TOTAL_CHARS:
                remain = MAX_TOTAL_CHARS - used
                if remain > 200:
                    text_blocks.append(f"### {name}\n{chunk[:remain]}")
                    sources.append(name)
                break
            text_blocks.append(f"### {name}\n{chunk}")
            sources.append(name)
            used += len(chunk)

        summary = "\n\n".join(text_blocks) if text_blocks else ""
        if not summary and learned:
            summary = str(learned)[:MAX_TOTAL_CHARS]

        logger.info(
            "StandardsProvider | sources=%s | chars=%s | learned=%s",
            sources,
            len(summary),
            len(learned),
        )

        return {
            "summary": summary,
            "sources": sources,
            "learned_standards": learned,
            "vault_notes_count": len(notes),
        }

    def _load_vault_standards(self) -> list[tuple[str, str]]:
        vault = Path(Config.OBSIDIAN_VAULT_PATH).expanduser()
        standards_dir = vault / "Standards"
        if not standards_dir.is_dir():
            logger.warning("Standards dir no existe: %s", standards_dir)
            return []

        by_name: dict[str, Path] = {p.name: p for p in standards_dir.glob("*.md") if p.is_file()}
        ordered: list[Path] = []
        for name in PREFERRED_NAMES:
            if name in by_name:
                ordered.append(by_name.pop(name))
        ordered.extend(sorted(by_name.values(), key=lambda p: p.name.lower()))

        result: list[tuple[str, str]] = []
        for path in ordered:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                logger.warning("No se pudo leer %s: %s", path, exc)
                continue
            result.append((path.name, text))
        return result
