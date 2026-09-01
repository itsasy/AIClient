from __future__ import annotations
import logging
from typing import Any
import requests

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import ProviderError, ProviderAuthenticationError

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    name = "openai"
    supports_tools = True

    def __init__(self) -> None:
        if not Config.OPENAI_API_KEY:
            raise ProviderAuthenticationError("OPENAI_API_KEY no está configurada.")
        self.api_key = Config.OPENAI_API_KEY
        self.model = getattr(Config, "OPENAI_MODEL", "gpt-4o-mini")

    def _ensure_string(self, content: Any) -> str:
        """Asegura que el contenido sea un string plano, desensamblando listas si es necesario."""
        if not content:
            return ""
        if isinstance(content, list):
            # Si el modelo devuelve una lista de partes, extrae el texto
            return " ".join([str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content])
        return str(content)

    def generate(self, prompt: Any, *, model: str | None = None, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 4096, **kwargs: Any) -> str:
        prompt_str = self._ensure_string(prompt)
        if not prompt_str.strip():
            raise ProviderError("El prompt no puede estar vacío.")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": self._ensure_string(system_prompt)})
        messages.append({"role": "user", "content": prompt_str})

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"].get("content")
            return self._ensure_string(content).strip()
        except requests.exceptions.RequestException as exc:
            raise ProviderError(f"Error HTTP en OpenAI API: {exc}")
        except Exception as e:
            raise ProviderError(f"Error parseando respuesta OpenAI: {e}")

    def generate_with_tools(self, prompt: Any, tools: list[Any], *, model: str | None = None, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 4096, **kwargs: Any) -> dict[str, Any] | str:
        prompt_str = self._ensure_string(prompt)
        if not prompt_str.strip():
            raise ProviderError("El prompt no puede estar vacío.")

        formatted_tools = []
        for t in tools:
            if isinstance(t, dict) and "name" in t:
                formatted_tools.append({"type": "function", "function": t})
            else:
                formatted_tools.append(t)

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": self._ensure_string(system_prompt)})
        messages.append({"role": "user", "content": prompt_str})

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": formatted_tools,
            "tool_choice": "auto"
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            
            if "tool_calls" in message and message["tool_calls"]:
                return {
                    "text": self._ensure_string(message.get("content")),
                    "tool_calls": message["tool_calls"]
                }
            
            return self._ensure_string(message.get("content")).strip()
            
        except requests.exceptions.RequestException as exc:
            raise ProviderError(f"Error HTTP en OpenAI API (tools): {exc}")
        except Exception as e:
            raise ProviderError(f"Error procesando tools en OpenAI: {e}")