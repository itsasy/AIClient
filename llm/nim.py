import requests

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import (
    LLMProviderError,
    LLMProviderUnavailableError,
)


class NIMProvider(LLMProvider):
    name = "nim"

    MODEL = "meta/llama-3.1-70b-instruct"
    TIMEOUT = 60

    def __init__(self):
        self.api_key = Config.NIM_API_KEY
        self.base_url = Config.NIM_BASE_URL.rstrip("/")

    def is_available(self) -> bool:
        return bool(
            self.api_key
            and self.base_url
        )

    def generate(self, prompt: str, **kwargs) -> str:
        if not prompt or not prompt.strip():
            raise LLMProviderError(
                "El prompt está vacío."
            )

        if not self.is_available():
            raise LLMProviderError(
                "NVIDIA NIM no está configurado."
            )

        model = kwargs.get("model", self.MODEL)

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": kwargs.get(
                "temperature",
                0.2,
            ),
            "max_tokens": kwargs.get(
                "max_tokens",
                4096,
            ),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.TIMEOUT,
            )

            if response.status_code >= 500:
                raise LLMProviderUnavailableError(
                    "NVIDIA NIM no está disponible temporalmente."
                )

            if response.status_code >= 400:
                raise LLMProviderError(
                    "NVIDIA NIM rechazó la solicitud: "
                    f"HTTP {response.status_code} - "
                    f"{response.text[:500]}"
                )

            data = response.json()

            choices = data.get("choices", [])

            if not choices:
                raise LLMProviderError(
                    "NVIDIA NIM no devolvió respuestas."
                )

            message = choices[0].get(
                "message",
                {},
            )

            content = message.get("content")

            if not content:
                raise LLMProviderError(
                    "NVIDIA NIM devolvió una respuesta vacía."
                )

            return content

        except requests.Timeout as exc:
            raise LLMProviderUnavailableError(
                "NVIDIA NIM excedió el tiempo de espera."
            ) from exc

        except requests.ConnectionError as exc:
            raise LLMProviderUnavailableError(
                "No se pudo conectar con NVIDIA NIM."
            ) from exc

        except requests.RequestException as exc:
            raise LLMProviderError(
                f"Error de comunicación con NVIDIA NIM: {exc}"
            ) from exc