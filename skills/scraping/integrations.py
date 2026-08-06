from __future__ import annotations

from typing import Any

import requests

from bs4 import BeautifulSoup

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class IntegrationScraperSkill(Skill):

    name = "scrape_integration"

    description = "Extrae información básica " "de integraciones externas."

    version = "2.0"

    capabilities = (
        "web_scraping",
        "integration_analysis",
    )

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

            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                },
                timeout=10,
            )

            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            title_node = soup.find("title")

            title = title_node.text if title_node else "Sin título"

            description = soup.get_text()[:1500]

            return {
                "ok": True,
                "result": {
                    "type": "integration_analysis",
                    "platform": platform,
                    "title": title,
                    "description": description,
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
