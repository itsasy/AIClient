from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill
from skills.scraping.page_scraper import PageScraper


class JobScraperSkill(Skill):

    name = "scrape_job"

    description = "Analiza publicaciones laborales de LinkedIn y Workana."

    version = "2.0"

    capabilities = (
        "web_scraping",
        "job_analysis",
        "market_research",
    )

    def __init__(self):

        self.scraper = PageScraper()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        url = params.get(
            "url",
            "",
        )

        platform = params.get(
            "platform",
            "unknown",
        )

        if not url:

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó URL.",
            }

        try:

            page = self.scraper.fetch(
                url,
            )

            description = page["text"][:1500]

            return {
                "ok": True,
                "result": {
                    "type": "job_analysis",
                    "platform": platform,
                    "title": page["title"],
                    "description": description,
                    "pain_points": self._analyze_pain(
                        description,
                    ),
                    "url": url,
                },
                "error": None,
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }

    def _analyze_pain(
        self,
        text: str,
    ) -> list[str]:

        keywords = [
            "problema",
            "error",
            "necesito",
            "busco",
            "ayuda",
            "solucionar",
            "urgente",
            "requerimiento",
        ]

        normalized = text.lower()

        return [keyword for keyword in keywords if keyword in normalized]
