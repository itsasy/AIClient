from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.config import Config
from core.analytics.models import ExecutionMetric

logger = logging.getLogger(__name__)


class MetricsStore:
    """
    Almacena y consulta métricas de ejecución en disco.
    """

    def __init__(self):
        self.metrics_dir = Config.PROJECT_ROOT / ".metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._cache: list[ExecutionMetric] = []

    def save(self, metric: ExecutionMetric) -> None:
        """Guarda una métrica en disco y en caché."""
        filename = f"{metric.execution_id}.json"
        path = self.metrics_dir / filename
        path.write_text(
            json.dumps(metric.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._cache.append(metric)
        if len(self._cache) > 1000:
            self._cache = self._cache[-500:]  # Limitar caché

    def list(self, limit: int = 100) -> list[ExecutionMetric]:
        """Lista las últimas N métricas."""
        if self._cache:
            return self._cache[-limit:]

        # Cargar desde disco
        files = sorted(self.metrics_dir.glob("*.json"), reverse=True)[:limit]
        metrics = []
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                metrics.append(ExecutionMetric.from_dict(data))
            except Exception:
                continue
        self._cache = metrics
        return metrics

    def get_aggregated(self) -> dict[str, Any]:
        """
        Devuelve estadísticas agregadas de las últimas ejecuciones.
        """
        metrics = self.list(limit=200)
        if not metrics:
            return {"total": 0}

        total = len(metrics)
        success = sum(1 for m in metrics if m.status == "success")
        failed = sum(1 for m in metrics if m.status == "failed")
        partial = sum(1 for m in metrics if m.status == "partial")

        # Por proveedor
        provider_stats = {}
        for m in metrics:
            p = m.provider
            if p not in provider_stats:
                provider_stats[p] = {"total": 0, "success": 0, "failed": 0}
            provider_stats[p]["total"] += 1
            if m.status == "success":
                provider_stats[p]["success"] += 1
            elif m.status == "failed":
                provider_stats[p]["failed"] += 1

        # Por skill (desde metadata)
        skill_stats = {}
        for m in metrics:
            skill = m.metadata.get("skill", "unknown")
            if skill not in skill_stats:
                skill_stats[skill] = {"total": 0, "success": 0, "failed": 0}
            skill_stats[skill]["total"] += 1
            if m.status == "success":
                skill_stats[skill]["success"] += 1
            elif m.status == "failed":
                skill_stats[skill]["failed"] += 1

        avg_duration = sum(m.duration for m in metrics) / total if total > 0 else 0

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "partial": partial,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "avg_duration": avg_duration,
            "provider_stats": provider_stats,
            "skill_stats": skill_stats,
            "latest": metrics[-1].to_dict() if metrics else None,
        }
