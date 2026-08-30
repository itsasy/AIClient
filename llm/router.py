from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

from core.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Punto único de comunicación con la capa LLM.

    Flujo:

        ExecutionPlan
            ↓
        ProviderSelector
            ↓
        PromptBuilder
            ↓
        ProviderManager
            ↓
        Provider
            ↓
        response

    Responsabilidades:

        - Seleccionar provider mediante ProviderSelector.
        - Construir el prompt mediante PromptBuilder.
        - Delegar la ejecución a ProviderManager.
        - Propagar el resultado o error.

    No:

        - Ejecuta directamente SDKs de proveedores.
        - Implementa fallback.
        - Decide qué provider utilizar.
        - Construye prompts directamente.
        - Conoce detalles específicos de Gemini,
          DeepSeek o NVIDIA NIM.
    """

    name = "llm_router"

    def __init__(
        self,
        provider_manager: ProviderManager | None = None,
        prompt_builder: PromptBuilder | None = None,
        tool_manager: ToolManager | None = None,
    ) -> None:

        self.provider_manager = provider_manager or ProviderManager()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.tool_manager = tool_manager or ToolManager()

    # =========================================================
    # Public API
    # =========================================================

    def generate(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Genera una respuesta utilizando el provider seleccionado
        para el ExecutionPlan.

        Args:
            plan:
                ExecutionPlan que define la intención,
                categoría y unidad de ejecución.

            context:
                Contexto adicional disponible para construir
                el prompt.

            kwargs:
                Parámetros adicionales enviados al provider.
                Ejemplos:
                    - model
                    - system_prompt
                    - temperature
                    - max_tokens

        Returns:
            Texto generado por el provider.

        Raises:
            ProviderError:
                Si el provider no puede procesar la solicitud.

            AllProvidersFailedError:
                Si todos los providers de la cadena de fallback
                fallan.
        """

        if plan is None:
            raise ValueError("LLMRouter requiere un ExecutionPlan.")

        context = dict(context or {})

        logger.info(
            "LLM Router iniciando | plan=%s | intent=%s | category=%s",
            plan.id,
            plan.intent,
            plan.intent_category,
        )

        # =====================================================
        # 1. Selección de provider
        # =====================================================

        provider, fallbacks = ProviderSelector.select(
            plan,
        )

        logger.info(
            "LLM Router provider seleccionado | " "provider=%s | fallbacks=%s | unit=%s:%s",
            provider,
            fallbacks,
            plan.execution_unit_type,
            plan.execution_unit,
        )

        # =====================================================
        # 2. Construcción del prompt
        # =====================================================

        prompt = self.prompt_builder.build(
            plan=plan,
            context=context,
        )

        logger.debug(
            "LLM Router prompt construido | plan=%s | chars=%s",
            plan.id,
            len(prompt),
        )

        # =====================================================
        # 3. Preparación de Tools
        # =====================================================
        allowed_tools = []
        if plan.allows_shell():
            allowed_tools.extend(["shell", "docker"])
        if plan.allows_write():
            allowed_tools.append("file")
            
        tools_schemas = self.tool_manager.get_schemas(allowed_names=allowed_tools) if allowed_tools else None
        
        if tools_schemas:
            logger.info("LLM Router habilitó tools | tools=%s", allowed_tools)

        # =====================================================
        # 4. Ejecución (con soporte opcional de loop de tools)
        # =====================================================

        try:
            if not tools_schemas:
                # Fallback al path antiguo sin tools
                response = self.provider_manager.generate(
                    prompt=prompt,
                    provider_name=provider,
                    fallback_chain=fallbacks,
                    **kwargs,
                )
            else:
                messages = [{"role": "user", "content": prompt}]
                max_iterations = 10
                iterations = 0
                
                while iterations < max_iterations:
                    iterations += 1
                    
                    llm_resp = self.provider_manager.generate_with_tools(
                        messages=messages,
                        provider_name=provider,
                        fallback_chain=fallbacks,
                        tools=tools_schemas,
                        **kwargs,
                    )
                    
                    if not llm_resp.tool_calls:
                        response = llm_resp.text or ""
                        break
                        
                    # Tiene tool calls
                    if llm_resp.text:
                        messages.append({"role": "assistant", "content": llm_resp.text})
                        
                    # Registramos la intención del asistente de llamar tools
                    tool_calls_payload = []
                    for tc in llm_resp.tool_calls:
                        tool_calls_payload.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": tc.arguments}
                        })
                    
                    # Añadimos el mensaje de tool_calls del assistant
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls_payload
                    })
                    
                    # Ejecutamos las tools y adjuntamos las respuestas
                    for tc in llm_resp.tool_calls:
                        logger.info("LLM Router ejecutando tool | name=%s", tc.name)
                        tool_result = self.tool_manager.execute(tc.name, **tc.arguments)
                        
                        tool_content = tool_result.get("error") if not tool_result.get("ok") else tool_result.get("result")
                        import json
                        if not isinstance(tool_content, str):
                            tool_content = json.dumps(tool_content, ensure_ascii=False, default=str)
                            
                        messages.append({
                            "role": "tool",
                            "name": tc.name,
                            "tool_call_id": tc.id,
                            "content": tool_content
                        })
                        
                        # Guardamos en metadata del plan para post-procesamiento (ej. ValidationRunner)
                        if "executed_tools" not in plan.metadata:
                            plan.metadata["executed_tools"] = []
                        plan.metadata["executed_tools"].append({
                            "name": tc.name,
                            "arguments": tc.arguments,
                            "result": tool_result
                        })
                        
                if iterations >= max_iterations:
                    logger.warning("LLM Router alcanzó límite de interaciones de tools | plan=%s", plan.id)
                    # Forzamos cierre con la última respuesta
                    response = llm_resp.text or ""

        except Exception:

            logger.exception(
                "LLM Router ejecución fallida | plan=%s | provider=%s",
                plan.id,
                provider,
            )

            raise

        # =====================================================
        # 5. Validación mínima de respuesta
        # =====================================================

        if not response or not response.strip():

            logger.error(
                "LLM Router recibió respuesta vacía | plan=%s | provider=%s",
                plan.id,
                provider,
            )

            raise RuntimeError("El proveedor LLM devolvió una respuesta vacía.")

        logger.info(
            "LLM Router ejecución completada | plan=%s | provider=%s | chars=%s",
            plan.id,
            provider,
            len(response),
        )

        return response.strip()
