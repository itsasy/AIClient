from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill
from skills.scraping.page_scraper import PageScraper


class JobScraperSkill(Skill):
    """
    Analiza publicaciones laborales obtenidas desde fuentes web.

    Responsabilidades:

    - Extraer contenido de una publicación.
    - Normalizar información básica.
    - Detectar señales de necesidad/problema.

    No:

    - Busca oportunidades automáticamente.
    - Contacta clientes.
    - Decide estrategia comercial.
    - Ejecuta acciones externas.
    """

    name = "scrape_job"

    description = "Analiza publicaciones laborales de plataformas como LinkedIn y Workana."

    version = "2.2"

    capabilities = (
        "web_scraping",
        "job_analysis",
        "market_research",
        "lead_detection",
    )

    MAX_DESCRIPTION_LENGTH = 1500

    PAIN_KEYWORDS = (
        "problema",
        "error",
        "necesito",
        "busco",
        "ayuda",
        "solucionar",
        "urgente",
        "requerimiento",
        "automatizar",
        "mejorar",
        "integración",
        "integracion",
    )

    def __init__(
        self,
        scraper: PageScraper | None = None,
    ):

        self.scraper = scraper or PageScraper()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        url = self._get_string(
            params,
            "url",
        )

        platform = self._get_string(
            params,
            "platform",
            "unknown",
        )

        if not url:

            return self._error(
                "No se proporcionó URL.",
            )

        try:

            page = self.scraper.fetch(
                url,
            )

            title = page.get(
                "title",
                "Sin título",
            )

            description = page.get(
                "text",
                "",
            )[: self.MAX_DESCRIPTION_LENGTH]

            pain_points = self._analyze_pain(
                description,
            )

            return {
                "ok": True,
                "result": {
                    "type": "job_analysis",  # o "page_analysis" si preferís
                    "platform": platform,
                    "title": title,
                    "description": description,
                    "text": description,  # alias para materialize genérico
                    "summary": f"{title}\n\n{description}"[:2000],
                    "pain_points": pain_points,
                    "signals": self._build_signals(pain_points),
                    "url": url,
                },
                "error": None,
            }

        except Exception as exc:

            return self._error(
                str(exc),
            )

    def _analyze_pain(
        self,
        text: str,
    ) -> list[str]:

        normalized = text.lower()

        return [keyword for keyword in self.PAIN_KEYWORDS if keyword in normalized]

    def _build_signals(
        self,
        pain_points: list[str],
    ) -> list[str]:

        signals = []

        if pain_points:

            signals.append(
                "potential_client_need",
            )

        if any(
            item in pain_points
            for item in (
                "automatizar",
                "integración",
                "integracion",
            )
        ):

            signals.append(
                "automation_opportunity",
            )

        if "urgente" in pain_points:

            signals.append(
                "high_priority_need",
            )

        return signals

    def _get_string(
        self,
        params: dict[str, Any],
        key: str,
        default: str = "",
    ) -> str:

        value = params.get(
            key,
            default,
        )

        if not isinstance(
            value,
            str,
        ):

            return default

        return value.strip()

    def _error(
        self,
        message: str,
    ) -> dict[str, Any]:

        return {
            "ok": False,
            "result": None,
            "error": message,
        }
