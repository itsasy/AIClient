from __future__ import annotations

from typing import Any

import requests

from bs4 import BeautifulSoup

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class LinkedInScraperSkill(Skill):

    name = "linkedin_scrape"

    description = "Extrae información básica " "de páginas de LinkedIn."

    version = "2.0"

    capabilities = (
        "web_scraping",
        "linkedin_analysis",
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

            summary_node = soup.find(
                "meta",
                attrs={
                    "name": "description",
                },
            )

            summary = summary_node["content"] if summary_node else "Sin descripción"

            return {
                "ok": True,
                "result": {
                    "type": "linkedin_result",
                    "title": title,
                    "summary": summary[:500],
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
