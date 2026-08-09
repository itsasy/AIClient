from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.config import Config
from core.consolidation.models import ConsolidationProposal, ConsolidationReport, Interaction
from core.engram_memory import EngramMemory
from core.standards_learner import StandardsLearner

logger = logging.getLogger(__name__)


class DailyConsolidator:
    """
    Revisa las interacciones del día, detecta patrones y genera propuestas de consolidación.
    """

    def __init__(self):
        self.engram = EngramMemory()
        self.standards = StandardsLearner()
        self.reports_dir = Config.PROJECT_ROOT / ".memory" / "consolidation"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, days: int = 1) -> ConsolidationReport:
        """
        Genera un informe de consolidación para los últimos N días.
        """
        # 1. Recuperar interacciones del período
        interactions = self._get_interactions(days)

        # 2. Detectar patrones
        patterns = self._detect_patterns(interactions)

        # 3. Generar propuestas
        proposals = self._generate_proposals(interactions, patterns)

        # 4. Resumen
        summary = self._generate_summary(interactions, patterns, proposals)

        report = ConsolidationReport(
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            interactions=interactions,
            patterns=patterns,
            proposals=proposals,
            summary=summary,
        )

        # Guardar informe en disco
        self._save_report(report)

        return report

    def _get_interactions(self, days: int) -> list[Interaction]:
        """
        Recupera interacciones de Engram desde los últimos N días.
        """
        # Engram no tiene búsqueda por fecha directamente, así que buscamos todas
        # y filtramos por fecha en el contenido.
        # Alternativa: buscar "user_query" y "assistant_response" y filtrar.
        memories = self.engram.recall("interaction user assistant", limit=100)

        interactions = []
        since = datetime.now(timezone.utc) - timedelta(days=days)

        for m in memories:
            content = m.get("content", "")
            # Buscar timestamp en el contenido (formato: 2026-08-09 10:00:00)
            time_match = re.search(r"(\d{4}-\d{2}-\d{2})", content)
            if time_match:
                try:
                    date_str = time_match.group(1)
                    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if dt < since:
                        continue
                except Exception:
                    continue

            # Intentar extraer usuario y asistente
            user_match = re.search(r"Usuario:\s*(.+)", content, re.IGNORECASE)
            ass_match = re.search(r"Asistente:\s*(.+)", content, re.IGNORECASE)

            if user_match or ass_match:
                interaction = Interaction(
                    timestamp=datetime.now(timezone.utc),
                    user_query=user_match.group(1) if user_match else "",
                    assistant_response=ass_match.group(1) if ass_match else "",
                    success=True,  # asumimos éxito por defecto
                )
                interactions.append(interaction)

        return interactions

    def _detect_patterns(self, interactions: list[Interaction]) -> list[str]:
        """
        Detecta patrones en las interacciones.
        """
        patterns = []
        if not interactions:
            return patterns

        # Palabras clave frecuentes
        words = {}
        for i in interactions:
            for w in i.user_query.lower().split():
                if len(w) > 3:
                    words[w] = words.get(w, 0) + 1

        # Temas recurrentes (palabras que aparecen > 1 vez)
        for word, count in words.items():
            if count > 1 and len(interactions) > 2:
                patterns.append(f"Tema recurrente: '{word}' ({count} veces)")

        # Patrón de preferencias aprendidas
        for i in interactions:
            if "aprende" in i.user_query.lower() or "prefiero" in i.user_query.lower():
                patterns.append("Preferencia aprendida detectada")

        return patterns[:5]  # limitar a 5 patrones

    def _generate_proposals(
        self, interactions: list[Interaction], patterns: list[str]
    ) -> list[ConsolidationProposal]:
        """
        Genera propuestas de consolidación a partir de las interacciones y patrones.
        """
        proposals = []

        # 1. Detectar nuevas preferencias
        for i in interactions:
            if "aprende" in i.user_query.lower() or "prefiero" in i.user_query.lower():
                # Extraer posible clave/valor
                match = re.search(
                    r"(aprende|prefiero)\s+que\s+(\w+)\s+es\s+(\w+)", i.user_query.lower()
                )
                if match:
                    key = match.group(2)
                    value = match.group(3)
                    proposals.append(
                        ConsolidationProposal(
                            type="standard",
                            key=key,
                            new_value=value,
                            reason=f"Detectado en: {i.user_query[:100]}",
                            source="automatic",
                        )
                    )

        # 2. Patrones de temas recurrentes → sugerir crear una Spec
        for pattern in patterns:
            if "Tema recurrente" in pattern:
                proposals.append(
                    ConsolidationProposal(
                        type="spec",
                        reason=f"Patrón detectado: {pattern}",
                        source="automatic",
                    )
                )

        return proposals

    def _generate_summary(self, interactions, patterns, proposals) -> str:
        lines = []
        lines.append(f"Interacciones analizadas: {len(interactions)}")
        if patterns:
            lines.append(f"Patrones detectados: {len(patterns)}")
        if proposals:
            lines.append(f"Propuestas generadas: {len(proposals)}")
        return "; ".join(lines)

    def _save_report(self, report: ConsolidationReport) -> None:
        """Guarda el informe en disco como pending-*.md"""
        filename = f"pending-{report.date}.md"
        path = self.reports_dir / filename

        content = f"""# Informe de consolidación - {report.date}

## Resumen
{report.summary}

## Interacciones
{len(report.interactions)} interacciones registradas.

## Patrones detectados
{chr(10).join(f"- {p}" for p in report.patterns) if report.patterns else "Ninguno"}

## Propuestas de consolidación
{chr(10).join(f"- [{p.type}] {p.reason}" for p in report.proposals) if report.proposals else "Ninguna"}

## Detalle de propuestas
"""
        for p in report.proposals:
            content += f"""
### {p.type.upper()} - {p.key or 'nueva'}
- **Motivo:** {p.reason}
- **Nuevo valor:** {p.new_value or 'pendiente'}
- **Fuente:** {p.source}
"""

        content += """

---
*Este informe fue generado automáticamente por AIClient.*
*Para revisar y aprobar cambios, ejecuta `ai --review`.*
"""

        path.write_text(content, encoding="utf-8")
        logger.info("Informe de consolidación guardado en %s", path)

    def list_pending(self) -> list[Path]:
        """Lista los informes pendientes de revisión."""
        return sorted(self.reports_dir.glob("pending-*.md"))

    def mark_done(self, report_path: Path) -> None:
        """Marca un informe como completado (renombra a done-*)."""
        if report_path.exists():
            new_name = report_path.name.replace("pending-", "done-")
            new_path = report_path.parent / new_name
            report_path.rename(new_path)
            logger.info("Informe marcado como completado: %s", new_path)
