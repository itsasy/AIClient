from __future__ import annotations

from typing import Any

import requests

from bs4 import BeautifulSoup

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class FreelanceScraperSkill(Skill):

    name = "scrape_freelance"

    description = "Analiza páginas de trabajos " "freelance y extrae información."

    version = "2.0"

    capabilities = (
        "web_scraping",
        "job_analysis",
        "freelance_analysis",
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
            "linkedin",
        )

        mode = params.get(
            "mode",
            "freelance",
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

            description_node = soup.find(
                "meta",
                attrs={
                    "name": "description",
                },
            )

            description = (
                description_node["content"] if description_node else soup.get_text()[:1200]
            )

            return {
                "ok": True,
                "result": {
                    "type": "freelance_analysis",
                    "platform": platform,
                    "mode": mode,
                    "title": title,
                    "description": description[:1000],
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

        result = [word for word in keywords if word in text.lower()]

        return result or ["No se identificaron dolores claros"]
