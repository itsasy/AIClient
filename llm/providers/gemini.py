from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import errors
from google.genai.types import GenerateContentConfig

from core.config import Config
from llm.base import LLMProvider
from llm.types import LLMResponse, ToolCall
from llm.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):

    name = "gemini"

    DEFAULT_SYSTEM_PROMPT = (
        "You are a senior software architect "
        "and AI coding assistant."
    )

    def __init__(self) -> None:

        if not Config.GEMINI_API_KEY:
            raise ProviderAuthenticationError(
                "GEMINI_API_KEY no está configurada."
            )

        self.client = genai.Client(
            api_key=Config.GEMINI_API_KEY,
        )

        self.model = Config.GEMINI_MODEL

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:

        if not prompt or not prompt.strip():
            raise ProviderError(
                "El prompt no puede estar vacío."
            )

        selected_model = model or self.model

        selected_system_prompt = (
            system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )

        logger.info(
            "Gemini request | model=%s",
            selected_model,
        )

        try:

            response = self.client.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=GenerateContentConfig(
                    system_instruction=selected_system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            text = getattr(
                response,
                "text",
                None,
            )

            if text:
                return text.strip()

            candidates = getattr(
                response,
                "candidates",
                None,
            )

            if candidates:

                try:

                    parts = candidates[0].content.parts

                    text = "".join(
                        getattr(
                            part,
                            "text",
                            "",
                        )
                        for part in parts
                    ).strip()

                    if text:
                        return text

                except Exception:

                    logger.debug(
                        "No se pudo extraer texto "
                        "desde candidates de Gemini.",
                        exc_info=True,
                    )

            raise ProviderError(
                "Gemini devolvió una respuesta vacía."
            )

        except errors.ClientError as exc:

            status_code = getattr(
                exc,
                "code",
                None,
            )

            if status_code in (401, 403):

                raise ProviderAuthenticationError(
                    f"Error de autenticación en Gemini: {exc}"
                ) from exc

            if status_code == 429:

                raise ProviderRateLimitError(
                    f"Gemini alcanzó el límite de uso: {exc}"
                ) from exc

            raise ProviderError(
                f"Error de cliente en Gemini: {exc}"
            ) from exc

        except errors.ServerError as exc:

            raise ProviderUnavailableError(
                f"Gemini no está disponible temporalmente: {exc}"
            ) from exc

        except (
            ProviderAuthenticationError,
            ProviderRateLimitError,
            ProviderUnavailableError,
            ProviderError,
        ):
            raise

        except errors.APIError as exc:

            raise ProviderError(
                f"Error de API de Gemini: {exc}"
            ) from exc

        except Exception as exc:

            logger.exception(
                "Error inesperado usando Gemini | model=%s",
                selected_model,
            )

            raise ProviderError(
                f"Error inesperado en Gemini: {exc}"
            ) from exc

    def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        
        selected_model = model or self.model
        selected_system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

        # Convertir messages (OpenAI format) a Gemini contents
        contents = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "system":
                # Si hay multiples system prompts, los concatenamos al system_instruction?
                # O los ignoramos y confiamos en system_prompt.
                continue
                
            gemini_role = "model" if role == "assistant" else "user"
            
            parts = []
            if content:
                parts.append({"text": content})
                
            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    parts.append({
                        "function_call": {
                            "name": tc["function"]["name"],
                            "args": tc["function"]["arguments"]
                        }
                    })
                    
            if role == "tool":
                gemini_role = "user" # Gemini expects tool responses as user role?
                # Actually in google.genai, tool responses go into function_response
                parts.append({
                    "function_response": {
                        "name": msg["name"],
                        "response": {"result": content} # simplified
                    }
                })
                
            if not parts:
                continue
                
            contents.append({
                "role": gemini_role,
                "parts": parts
            })

        # Configurar tools
        genai_tools = []
        if tools:
            # Asumimos format de JSON schema de OpenAI
            # genai.types.Tool espera function_declarations
            # Pero SDK permite pasar JSON schema dicts
            from google.genai import types
            
            funcs = []
            for t in tools:
                func = t.get("function", {})
                funcs.append(
                    types.FunctionDeclaration(
                        name=func.get("name"),
                        description=func.get("description"),
                        parameters=func.get("parameters")
                    )
                )
            
            if funcs:
                genai_tools = [types.Tool(function_declarations=funcs)]

        try:
            response = self.client.models.generate_content(
                model=selected_model,
                contents=contents,
                config=GenerateContentConfig(
                    system_instruction=selected_system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    tools=genai_tools or None
                ),
            )

            text_response = ""
            tool_calls = []

            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if getattr(part, "text", None):
                        text_response += part.text
                    
                    fc = getattr(part, "function_call", None)
                    if fc:
                        tool_calls.append(
                            ToolCall(
                                id=fc.name, # Gemini no da ID, usamos name
                                name=fc.name,
                                arguments=fc.args or {}
                            )
                        )

            return LLMResponse(
                text=text_response.strip() if text_response else None,
                tool_calls=tool_calls
            )

        except Exception as exc:
            logger.exception("Error usando Gemini con tools | model=%s", selected_model)
            raise ProviderError(f"Error en Gemini con tools: {exc}") from exc