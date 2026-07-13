from google import genai
from google.genai import errors

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import (
    LLMProviderError,
    LLMProviderUnavailableError,
)


class GeminiProvider(LLMProvider):
    name = "gemini"
    MODEL = "gemini-2.5-flash"

    def __init__(self):
        self.client = None

        if self.is_available():
            self.client = genai.Client(
                api_key=Config.GEMINI_API_KEY,
            )

    def is_available(self) -> bool:
        return bool(Config.GEMINI_API_KEY)

    def generate(self, prompt: str, **kwargs) -> str:
        if not prompt or not prompt.strip():
            raise LLMProviderError(
                "El prompt está vacío."
            )

        if self.client is None:
            raise LLMProviderError(
                "Gemini no está configurado."
            )

        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=[prompt],
            )

            if not response or not response.text:
                raise LLMProviderError(
                    "Gemini no devolvió contenido."
                )

            return response.text

        except errors.ServerError as exc:
            raise LLMProviderUnavailableError(
                "Gemini no está disponible temporalmente."
            ) from exc

        except errors.APIError as exc:
            raise LLMProviderError(
                f"Error de API de Gemini: {exc}"
            ) from exc