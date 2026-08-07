from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Construye prompts para el LLM.

    Responsabilidad:

        structured context
            ↓
        task prompt

    No debe serializar indiscriminadamente todo el runtime.
    """

    MAX_CONTEXT_CHARS = 30_000

    SYSTEM_INSTRUCTIONS = """
Eres un arquitecto de software senior.

Analiza únicamente la evidencia proporcionada en el contexto.

Reglas obligatorias:

1. No inventes componentes.
2. No inventes tecnologías.
3. No afirmes que el sistema utiliza microservicios salvo que
   exista evidencia explícita de ello.
4. No confundas carpetas con límites arquitectónicos.
5. Diferencia hechos observados de inferencias.
6. Si la evidencia no permite determinar algo, indícalo.
7. Prioriza la arquitectura real sobre descripciones genéricas.
8. Responde en español.
""".strip()

    def __init__(
        self,
        max_context_chars: int | None = None,
    ) -> None:

        self.max_context_chars = max_context_chars or self.MAX_CONTEXT_CHARS

    # ==========================================================
    # Public API
    # ==========================================================

    def build(
        self,
        plan: Any,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = dict(
            context or {},
        )

        intent = getattr(
            plan,
            "intent",
            None,
        )

        original_task = getattr(
            plan,
            "original_task",
            "",
        )

        unit_type = getattr(
            plan,
            "execution_unit_type",
            None,
        )

        unit_name = getattr(
            plan,
            "execution_unit",
            None,
        )

        logger.info(
            "Construyendo prompt | context=%s",
            list(context.keys()),
        )

        compact_context = self._prepare_context(
            context,
        )

        serialized_context = self._serialize(
            compact_context,
        )

        if len(serialized_context) > self.max_context_chars:
            logger.warning(
                "Contexto excede límite | chars=%s | max=%s",
                len(serialized_context),
                self.max_context_chars,
            )

            serialized_context = self._truncate_context(
                serialized_context,
            )

        prompt = self._compose(
            original_task=original_task,
            intent=intent,
            unit_type=unit_type,
            unit_name=unit_name,
            context=serialized_context,
        )

        logger.info(
            "Prompt construido chars=%s",
            len(prompt),
        )

        return prompt

    # ==========================================================
    # Context preparation
    # ==========================================================

    def _prepare_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        prepared: dict[str, Any] = {}

        # ------------------------------------------------------
        # Agent role
        # ------------------------------------------------------

        if "agent_role" in context:
            prepared["agent_role"] = context["agent_role"]

        # ------------------------------------------------------
        # Analysis requirements
        # ------------------------------------------------------

        if "analysis_requirements" in context:
            prepared["analysis_requirements"] = context["analysis_requirements"]

        # ------------------------------------------------------
        # Requested output
        # ------------------------------------------------------

        if "requested_output" in context:
            prepared["requested_output"] = context["requested_output"]

        # ------------------------------------------------------
        # Project summary
        # ------------------------------------------------------

        if "project_summary" in context:
            prepared["project_summary"] = context["project_summary"]

        # ------------------------------------------------------
        # Architecture
        # ------------------------------------------------------

        if "architecture" in context:
            prepared["architecture"] = self._sanitize_architecture(
                context["architecture"],
            )

        # ------------------------------------------------------
        # Execution
        # ------------------------------------------------------

        if "execution" in context:
            prepared["execution"] = self._sanitize_execution(
                context["execution"],
            )

        return prepared

    # ==========================================================
    # Architecture sanitization
    # ==========================================================

    def _sanitize_architecture(
        self,
        architecture: Any,
    ) -> Any:

        if not isinstance(
            architecture,
            dict,
        ):
            return architecture

        result = dict(
            architecture,
        )

        files = result.get(
            "files",
        )

        if isinstance(
            files,
            list,
        ):
            clean_files = []

            for file_data in files:
                if not isinstance(
                    file_data,
                    dict,
                ):
                    continue

                clean_files.append(
                    {
                        key: file_data.get(key)
                        for key in (
                            "path",
                            "filename",
                            "extension",
                            "language",
                            "lines",
                            "size",
                        )
                        if key in file_data
                    }
                )

            result["files"] = clean_files

        directories = result.get(
            "directories",
        )

        if isinstance(
            directories,
            list,
        ):
            result["directories"] = [
                self._sanitize_directory(
                    item,
                )
                for item in directories
            ]

        # Never allow source content through
        # the architecture context.
        result.pop(
            "content",
            None,
        )

        return result

    @staticmethod
    def _sanitize_directory(
        directory: Any,
    ) -> Any:

        if not isinstance(
            directory,
            dict,
        ):
            return directory

        return {
            key: directory.get(key)
            for key in (
                "path",
                "name",
                "files_count",
                "directories_count",
            )
            if key in directory
        }

    # ==========================================================
    # Execution sanitization
    # ==========================================================

    @staticmethod
    def _sanitize_execution(
        execution: Any,
    ) -> Any:

        if not isinstance(
            execution,
            dict,
        ):
            return execution

        return {
            key: execution.get(key)
            for key in (
                "plan_id",
                "intent",
                "original_task",
                "current_step",
            )
            if key in execution
        }

    # ==========================================================
    # Serialization
    # ==========================================================

    @staticmethod
    def _serialize(
        value: Any,
    ) -> str:

        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        except Exception:
            return str(value)

    # ==========================================================
    # Truncation
    # ==========================================================

    def _truncate_context(
        self,
        serialized: str,
    ) -> str:

        limit = self.max_context_chars

        if len(serialized) <= limit:
            return serialized

        truncated = serialized[:limit]

        return (
            truncated + "\n\n"
            "[SYSTEM NOTICE]\n"
            "El contexto fue limitado por tamaño. "
            "No inferir información ausente."
        )

    # ==========================================================
    # Prompt composition
    # ==========================================================

    def _compose(
        self,
        original_task: str,
        intent: str | None,
        unit_type: str | None,
        unit_name: str | None,
        context: str,
    ) -> str:

        return f"""
{self.SYSTEM_INSTRUCTIONS}

## Tarea del usuario

{original_task}

## Intent

{intent or "unknown"}

## Unidad ejecutora

{unit_type or "unknown"}:{unit_name or "unknown"}

## Contexto disponible

{context}

## Instrucciones de análisis

Realiza el análisis solicitado utilizando únicamente el contexto
proporcionado.

Cuando describas la arquitectura:

- identifica primero lo que está explícitamente observado;
- después explica las relaciones que puedan inferirse;
- no presentes inferencias como hechos;
- no inventes patrones arquitectónicos;
- no inventes infraestructura;
- no inventes comunicación entre servicios;
- no describas el sistema como microservicios sin evidencia.

Entrega un análisis ejecutivo, concreto y específico para este proyecto.
""".strip()
