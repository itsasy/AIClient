from __future__ import annotations

import ipaddress

from urllib.parse import urlparse

import requests

from bs4 import BeautifulSoup


class PageScraper:
    """
    Cliente HTTP para extracción de contenido web.

    Responsabilidades:

    - Descargar páginas.
    - Validar URLs.
    - Extraer texto visible.

    No:

    - Analiza intención.
    - Ejecuta Skills.
    - Decide procesamiento posterior.
    """

    DEFAULT_TIMEOUT = 10

    MAX_CONTENT_SIZE = 5_000_000

    USER_AGENT = "Mozilla/5.0 " "(compatible; EngramBot/1.0)"

    RETRIES = 2

    def __init__(
        self,
        timeout: int | None = None,
    ):

        self.timeout = timeout or self.DEFAULT_TIMEOUT

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
            }
        )

    def fetch(
        self,
        url: str,
    ) -> dict[str, str]:

        self._validate_url(
            url,
        )

        last_error = None

        for _ in range(self.RETRIES + 1):

            try:

                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    stream=True,
                    allow_redirects=True,
                )

                response.raise_for_status()

                content_type = response.headers.get(
                    "content-type",
                    "",
                )

                if "text/html" not in content_type:

                    raise RuntimeError("Contenido no HTML.")

                content = response.raw.read(
                    self.MAX_CONTENT_SIZE + 1,
                )

                if len(content) > self.MAX_CONTENT_SIZE:

                    raise RuntimeError("Página supera tamaño máximo permitido.")

                html = content.decode(
                    response.encoding or "utf-8",
                    errors="replace",
                )

                return self._parse(
                    html,
                    url,
                )

            except requests.RequestException as exc:

                last_error = exc

        raise RuntimeError(f"Error obteniendo página: {last_error}")

    def _parse(
        self,
        html: str,
        url: str,
    ) -> dict[str, str]:

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        title_node = soup.find(
            "title",
        )

        return {
            "title": (
                title_node.get_text(
                    strip=True,
                )
                if title_node
                else "Sin título"
            ),
            "text": soup.get_text(
                " ",
                strip=True,
            ),
            "url": url,
        }

    def _validate_url(
        self,
        url: str,
    ) -> None:

        if not url:

            raise ValueError("URL vacía.")

        parsed = urlparse(
            url,
        )

        if parsed.scheme not in {
            "http",
            "https",
        }:

            raise ValueError("Solo HTTP/HTTPS permitido.")

        if not parsed.hostname:

            raise ValueError("URL sin dominio.")

        self._validate_host(
            parsed.hostname,
        )

    def _validate_host(
        self,
        hostname: str,
    ) -> None:

        try:

            ip = ipaddress.ip_address(
                hostname,
            )

            if ip.is_private or ip.is_loopback or ip.is_reserved:

                raise ValueError("IP privada no permitida.")

        except ValueError:

            # Dominio normal.
            return
