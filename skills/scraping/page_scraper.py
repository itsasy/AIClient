from __future__ import annotations

import requests

from bs4 import BeautifulSoup


class PageScraper:

    def fetch(
        self,
        url: str,
    ) -> dict[str, str]:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
            timeout=10,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title_node = soup.find("title")

        return {
            "title": (title_node.text.strip() if title_node else "Sin título"),
            "text": soup.get_text(
                " ",
                strip=True,
            ),
            "url": url,
        }
