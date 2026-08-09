from __future__ import annotations

import logging
from typing import Any

from core.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


class Analyzer:
    """
    Analiza métricas y genera recomendaciones.
    """

    def __init__(self):
        self.store = MetricsStore()

    def analyze(self) -> dict[str, Any]:
        """
        Genera un informe de análisis completo.
        """
        agg = self.store.get_aggregated()

        report = {
            "summary": agg,
            "recommendations": self._generate_recommendations(agg),
            "top_issues": self._find_top_issues(agg),
        }
        return report

    def _generate_recommendations(self, agg: dict[str, Any]) -> list[str]:
        """
        Genera recomendaciones basadas en métricas.
        """
        recommendations = []

        # 1. Recomendar proveedor con mejor tasa de éxito
        provider_stats = agg.get("provider_stats", {})
        if provider_stats:
            best_provider = max(
                provider_stats.items(),
                key=lambda x: x[1]["success"] / x[1]["total"] if x[1]["total"] > 0 else 0,
                default=None,
            )
            if best_provider:
                name, stats = best_provider
                rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
                if rate > 80:
                    recommendations.append(
                        f"✅ El proveedor '{name}' tiene la mejor tasa de éxito ({rate:.1f}%). Considera usarlo como predeterminado."
                    )

        # 2. Skills con baja tasa de éxito
        skill_stats = agg.get("skill_stats", {})
        for skill, stats in skill_stats.items():
            total = stats["total"]
            success = stats["success"]
            if total > 5 and (success / total) < 0.5:
                recommendations.append(
                    f"⚠️ La skill '{skill}' tiene baja tasa de éxito ({success}/{total}). Revisa su implementación."
                )

        # 3. Recomendar optimización de tiempo
        avg_duration = agg.get("avg_duration", 0)
        if avg_duration > 60:
            recommendations.append(
                f"⏱️ El tiempo promedio de ejecución es alto ({avg_duration:.1f}s). Considera usar un modelo más rápido para tareas simples."
            )

        # 4. Sugerir SelfCritic si no está activo
        # (se puede inferir de metadata, pero simplificamos)
        if agg.get("total", 0) > 10 and agg.get("success_rate", 0) < 70:
            recommendations.append(
                "🔍 La tasa de éxito es baja. Considera habilitar SelfCritic para mejorar la calidad (requires_self_critic: True en el plan)."
            )

        return recommendations[:5]  # limitar a 5 recomendaciones

    def _find_top_issues(self, agg: dict[str, Any]) -> list[str]:
        """
        Encuentra problemas comunes en las ejecuciones.
        """
        issues = []
        # Analizar errores de las últimas ejecuciones
        metrics = self.store.list(limit=50)
        errors = [m.error for m in metrics if m.error]
        if errors:
            # Contar errores comunes
            from collections import Counter

            counter = Counter(errors)
            for error, count in counter.most_common(3):
                issues.append(f"Error frecuente: '{error[:50]}...' ({count} veces)")
        return issues
