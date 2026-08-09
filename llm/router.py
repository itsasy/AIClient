from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

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
    ) -> None:

        self.provider_manager = provider_manager or ProviderManager()

        self.prompt_builder = prompt_builder or PromptBuilder()

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
        # 3. Ejecución
        # =====================================================

        try:

            response = self.provider_manager.generate(
                prompt=prompt,
                provider_name=provider,
                fallback_chain=fallbacks,
                **kwargs,
            )

        except Exception:

            logger.exception(
                "LLM Router ejecución fallida | " "plan=%s | provider=%s",
                plan.id,
                provider,
            )

            raise

        # =====================================================
        # 4. Validación mínima de respuesta
        # =====================================================

        if not response or not response.strip():

            logger.error(
                "LLM Router recibió respuesta vacía | " "plan=%s | provider=%s",
                plan.id,
                provider,
            )

            raise RuntimeError("El proveedor LLM devolvió una respuesta vacía.")

        logger.info(
            "LLM Router ejecución completada | " "plan=%s | provider=%s | chars=%s",
            plan.id,
            provider,
            len(response),
        )

        return response.strip()
