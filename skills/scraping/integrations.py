from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill
from skills.scraping.page_scraper import PageScraper


class IntegrationScraperSkill(Skill):

    name = "scrape_integration"

    description = "Extrae información básica de integraciones externas."

    version = "2.0"

    capabilities = (
        "web_scraping",
        "integration_analysis",
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

            return {
                "ok": True,
                "result": {
                    "type": "integration_analysis",
                    "platform": platform,
                    "title": page["title"],
                    "description": page["text"][:1500],
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
