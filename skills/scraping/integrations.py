from skills.base import Skill
import requests
from bs4 import BeautifulSoup


class IntegrationScraperSkill(Skill):
    name = "scrape_integration"
    description = "Scraping para LinkedIn, Workana, GitHub"

    def execute(self, url: str, platform: str = "linkedin", **kwargs):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("title").text if soup.find("title") else "Sin título"
            description = soup.get_text()[:1500]

            return {
                "type": "integration_analysis",
                "payload": {
                    "ok": True,
                    "platform": platform,
                    "title": title,
                    "description": description,
                    "url": url,
                },
            }
        except Exception as e:
            return {
                "type": "integration_analysis",
                "payload": {"ok": False, "error": str(e)},
            }
