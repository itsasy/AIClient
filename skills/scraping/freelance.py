from skills.base import Skill
import requests
from bs4 import BeautifulSoup


class FreelanceScraperSkill(Skill):
    name = "scrape_freelance"
    description = "Analiza trabajos en Workana, LinkedIn, etc."

    def execute(
        self, url: str, platform: str = "linkedin", mode: str = "freelance", **kwargs
    ):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("title").text if soup.find("title") else "Sin título"
            description = soup.find("meta", attrs={"name": "description"})
            description = (
                description["content"] if description else soup.get_text()[:1200]
            )

            pain_points = self._analyze_pain(description)

            return {
                "type": "freelance_analysis",
                "payload": {
                    "ok": True,
                    "platform": platform,
                    "mode": mode,  # "freelance" o "job"
                    "title": title,
                    "description": description[:1000],
                    "pain_points": pain_points,
                    "url": url,
                },
            }
        except Exception as e:
            return {
                "type": "freelance_analysis",
                "payload": {"ok": False, "error": str(e)},
            }

    def _analyze_pain(self, text: str):
        pain_keywords = [
            "problema",
            "error",
            "necesito",
            "busco",
            "ayuda",
            "solucionar",
            "urgente",
            "requerimiento",
        ]
        pains = [word for word in pain_keywords if word in text.lower()]
        return pains or ["No se identificaron dolores claros"]
