from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.analytics.models import ExecutionMetric
from core.config import Config

logger = logging.getLogger(__name__)


class MetricsStore:
    """
    Almacena y consulta métricas de ejecución en disco.
    """

    def __init__(self) -> None:
        self.metrics_dir: Path = Config.PROJECT_ROOT / ".metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self._cache: list[ExecutionMetric] = []

    # =========================================================
    # Persistence
    # =========================================================

    def save(
        self,
        metric: ExecutionMetric,
    ) -> None:
        """Guarda una métrica en disco y en caché."""

        if not isinstance(metric, ExecutionMetric):
            raise TypeError("MetricsStore.save requiere un ExecutionMetric.")

        filename = f"{metric.execution_id}.json"
        path = self.metrics_dir / filename

        path.write_text(
            json.dumps(
                metric.to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self._cache.append(metric)

        if len(self._cache) > 1000:
            self._cache = self._cache[-500:]

    # =========================================================
    # Query
    # =========================================================

    def list(
        self,
        limit: int = 100,
    ) -> list[ExecutionMetric]:
        """Lista las últimas N métricas."""

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit debe ser un entero.")

        if limit <= 0:
            return []

        if self._cache:
            return self._cache[-limit:]

        files = sorted(
            self.metrics_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:limit]

        metrics: list[ExecutionMetric] = []

        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))

                metrics.append(ExecutionMetric.from_dict(data))

            except Exception as exc:
                logger.warning(
                    "No se pudo cargar métrica %s: %s",
                    path.name,
                    exc,
                )

        self._cache = list(reversed(metrics))

        return self._cache[-limit:]

    # =========================================================
    # Aggregation
    # =========================================================

    def get_aggregated(self) -> dict[str, Any]:
        """
        Devuelve estadísticas agregadas de las últimas ejecuciones.
        """

        metrics = self.list(limit=200)

        if not metrics:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "partial": 0,
                "cancelled": 0,
                "success_rate": 0,
                "avg_duration": 0,
                "provider_stats": {},
                "skill_stats": {},
                "latest": None,
            }

        total = len(metrics)

        success = sum(1 for metric in metrics if metric.status == "completed")

        failed = sum(1 for metric in metrics if metric.status == "failed")

        partial = sum(1 for metric in metrics if metric.status == "partial")

        cancelled = sum(1 for metric in metrics if metric.status == "cancelled")

        # =====================================================
        # Provider statistics
        # =====================================================

        provider_stats: dict[str, dict[str, int]] = {}

        for metric in metrics:
            provider = metric.provider

            if provider not in provider_stats:
                provider_stats[provider] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                }

            provider_stats[provider]["total"] += 1

            if metric.status == "completed":
                provider_stats[provider]["success"] += 1

            elif metric.status == "failed":
                provider_stats[provider]["failed"] += 1

        # =====================================================
        # Skill statistics
        # =====================================================

        skill_stats: dict[str, dict[str, int]] = {}

        for metric in metrics:
            skill = metric.metadata.get(
                "skill",
                "unknown",
            )

            if skill not in skill_stats:
                skill_stats[skill] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                }

            skill_stats[skill]["total"] += 1

            if metric.status == "completed":
                skill_stats[skill]["success"] += 1

            elif metric.status == "failed":
                skill_stats[skill]["failed"] += 1

        # =====================================================
        # Duration
        # =====================================================

        avg_duration = sum(metric.duration for metric in metrics) / total

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "partial": partial,
            "cancelled": cancelled,
            "success_rate": (success / total * 100 if total > 0 else 0),
            "avg_duration": avg_duration,
            "provider_stats": provider_stats,
            "skill_stats": skill_stats,
            "latest": metrics[-1].to_dict(),
        }
