from __future__ import annotations

import json
import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from llm.prompt_builder import PromptBuilder, PromptType
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class SelfCritic:
    """
    Evaluador post-ejecución.

    Responsabilidades:
        - Determinar si una ejecución requiere evaluación.
        - Construir el contexto de evaluación.
        - Solicitar evaluación al LLM.
        - Parsear y validar la respuesta.
        - Normalizar el resultado.

    No:
        - Ejecuta nuevamente la tarea.
        - Decide el número de retries.
        - Modifica el ExecutionPlan.
        - Ejecuta Agents o Skills.
        - Selecciona proveedores.
        - Decide políticas de ejecución.

    El contexto de evaluación debe ser proporcionado
    explícitamente por el caller.

    SelfCritic NO accede a:
        plan.loaded_context

    Esto mantiene separado:
        - el contexto de ejecución
        - el contexto utilizado por el crítico
    """

    DEFAULT_SCORE = 5
    MIN_SCORE = 0
    MAX_SCORE = 10
    PASS_SCORE = 5

    REQUIRED_FIELDS = {
        "pass",
        "score",
        "issues",
        "corrections",
        "reason",
    }

    def __init__(
        self,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.prompt_builder = prompt_builder or PromptBuilder()

    # ==========================================================
    # Public API
    # ==========================================================

    def evaluate(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evalúa el resultado de una ejecución.

        SelfCritic no modifica el resultado original ni el plan.
        Devuelve únicamente un contrato de evaluación normalizado.

        El contexto debe ser recibido explícitamente mediante
        el argumento `context`.

        Importante:
            SelfCritic nunca utiliza plan.loaded_context.
        """

        if plan is None:
            raise ValueError(
                "plan no puede ser None.",
            )

        if result is None:
            raise ValueError(
                "result no puede ser None.",
            )

        logger.info(
            "Evaluando ejecución | plan=%s | status=%s",
            plan.id,
            getattr(
                result,
                "status",
                None,
            ),
        )

        # ------------------------------------------------------
        # Resultado fallido
        # ------------------------------------------------------

        if result.is_failure:
            evaluation = self._evaluation_from_failure(
                result,
            )

            logger.info(
                "SelfCritic omitido por ejecución fallida | plan=%s",
                plan.id,
            )

            return evaluation

        # ------------------------------------------------------
        # Self-critic no requerido
        # ------------------------------------------------------

        requires_self_critic = bool(
            plan.metadata.get(
                "requires_self_critic",
                False,
            )
        )

        if not requires_self_critic:
            return self._evaluation_pass(
                score=10,
                reason="No se requirió crítica.",
            )

        # ------------------------------------------------------
        # Contexto explícito
        # ------------------------------------------------------

        context = context or {}

        # ------------------------------------------------------
        # Construcción del contexto de evaluación
        # ------------------------------------------------------

        evaluation_context = self._build_context(
            plan=plan,
            result=result,
            context=context,
        )

        try:
            # --------------------------------------------------
            # Construcción del prompt especializado
            # --------------------------------------------------

            prompt = self.prompt_builder.build(
                plan=plan,
                context=evaluation_context,
                prompt_type=PromptType.CRITIQUE,
            )

            logger.debug(
                "Prompt de SelfCritic construido | plan=%s | chars=%s",
                plan.id,
                len(prompt),
            )

            # --------------------------------------------------
            # Evaluación mediante LLMRouter
            # --------------------------------------------------

            response = LLMRouter().generate(
                plan=plan,
                context={
                    "prompt": prompt,
                    "prompt_type": PromptType.CRITIQUE.value,
                },
            )

            if not isinstance(
                response,
                str,
            ):
                logger.warning(
                    "SelfCritic recibió respuesta no textual | " "plan=%s | type=%s",
                    plan.id,
                    type(response).__name__,
                )

                return self._evaluation_unavailable(
                    reason=("El LLM devolvió una respuesta " "que no es texto."),
                )

            evaluation = self._parse_and_validate(
                response,
            )

            logger.info(
                "SelfCritic completado | plan=%s | status=%s | " "pass=%s | score=%s",
                plan.id,
                evaluation.get("status"),
                evaluation.get("pass"),
                evaluation.get("score"),
            )

            return evaluation

        except Exception as exc:
            logger.exception(
                "Error durante SelfCritic | plan=%s",
                plan.id,
            )

            return self._evaluation_unavailable(
                reason=f"Error en crítica: {exc}",
            )

    # ==========================================================
    # Context
    # ==========================================================

    def _build_context(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Construye la evidencia que necesita el crítico.

        El contexto base proviene exclusivamente del argumento
        `context`.

        No se consulta:
            plan.loaded_context

        Se agrega información de la ejecución actual para que
        el crítico pueda evaluar el resultado.
        """

        source_context = dict(
            context or {},
        )

        evaluation_context: dict[str, Any] = dict(
            source_context,
        )

        # ------------------------------------------------------
        # Información de ejecución
        # ------------------------------------------------------

        existing_execution = evaluation_context.get(
            "execution",
        )

        execution_context: dict[str, Any] = {}

        if isinstance(
            existing_execution,
            dict,
        ):
            execution_context.update(
                existing_execution,
            )

        execution_context.update(
            {
                "plan_id": plan.id,
                "task": plan.original_task,
                "result": result.to_dict(),
            }
        )

        evaluation_context["execution"] = execution_context

        return evaluation_context

    # ==========================================================
    # Parsing
    # ==========================================================

    def _parse_and_validate(
        self,
        response: str,
    ) -> dict[str, Any]:
        """
        Extrae, valida y normaliza la respuesta del LLM.
        """

        if not response or not response.strip():
            return self._evaluation_unavailable(
                reason="El LLM no devolvió una respuesta.",
            )

        data = self._extract_json(
            response,
        )

        if data is None:
            return self._evaluation_unavailable(
                reason=("La respuesta del LLM no contiene " "JSON válido."),
            )

        if not self._has_valid_contract(
            data,
        ):
            return self._evaluation_unavailable(
                reason=("La respuesta JSON del LLM " "no cumple el contrato de evaluación."),
            )

        return self._normalize_evaluation(
            data,
        )

    def _extract_json(
        self,
        response: str,
    ) -> dict[str, Any] | None:
        """
        Extrae un objeto JSON de la respuesta del LLM.

        Se acepta:
            1. JSON puro.
            2. JSON rodeado accidentalmente por texto.

        No se ejecuta ni evalúa contenido arbitrario.
        """

        text = response.strip()

        # ------------------------------------------------------
        # Caso ideal: respuesta completamente JSON.
        # ------------------------------------------------------

        try:
            parsed = json.loads(
                text,
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            pass

        # ------------------------------------------------------
        # Fallback: localizar el primer objeto JSON.
        # ------------------------------------------------------

        start = text.find(
            "{",
        )

        end = text.rfind(
            "}",
        )

        if start == -1 or end == -1 or end <= start:
            return None

        candidate = text[start : end + 1]

        try:
            parsed = json.loads(
                candidate,
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            logger.warning(
                "SelfCritic recibió JSON inválido.",
            )

        return None

    # ==========================================================
    # Contract validation
    # ==========================================================

    def _has_valid_contract(
        self,
        data: dict[str, Any],
    ) -> bool:
        """
        Verifica que la respuesta del LLM contenga
        todos los campos requeridos y con tipos compatibles.
        """

        if not self.REQUIRED_FIELDS.issubset(
            data.keys(),
        ):
            return False

        if not isinstance(
            data.get("pass"),
            bool,
        ):
            return False

        if not self._is_valid_score(
            data.get("score"),
        ):
            return False

        if not self._is_valid_string_list(
            data.get("issues"),
        ):
            return False

        if not self._is_valid_string_list(
            data.get("corrections"),
        ):
            return False

        if not isinstance(
            data.get("reason"),
            str,
        ):
            return False

        return True

    @classmethod
    def _is_valid_score(
        cls,
        value: Any,
    ) -> bool:
        """
        Valida que score sea un entero entre 0 y 10.
        """

        return (
            isinstance(
                value,
                int,
            )
            and not isinstance(
                value,
                bool,
            )
            and cls.MIN_SCORE <= value <= cls.MAX_SCORE
        )

    @staticmethod
    def _is_valid_string_list(
        value: Any,
    ) -> bool:
        if not isinstance(
            value,
            list,
        ):
            return False

        return all(
            isinstance(
                item,
                str,
            )
            for item in value
        )

    # ==========================================================
    # Validation / normalization
    # ==========================================================

    def _normalize_evaluation(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normaliza la respuesta del LLM al contrato estable
        utilizado por ExecutionEngine y RetryPolicy.

        La puntuación es la fuente determinística del estado
        final de aprobación.
        """

        score = self._normalize_score(
            data.get("score"),
        )

        passed = score >= self.PASS_SCORE

        issues = self._normalize_string_list(
            data.get("issues"),
        )

        corrections = self._normalize_string_list(
            data.get("corrections"),
        )

        reason = str(
            data.get(
                "reason",
                "",
            )
        ).strip()

        return {
            "status": "completed",
            "pass": passed,
            "score": score,
            "issues": issues,
            "corrections": corrections,
            "reason": reason,
        }

    @classmethod
    def _normalize_score(
        cls,
        value: Any,
    ) -> int:
        """
        Normaliza la puntuación al rango 0..10.
        """

        try:
            score = int(
                value,
            )

        except (
            TypeError,
            ValueError,
        ):
            score = cls.DEFAULT_SCORE

        return max(
            cls.MIN_SCORE,
            min(
                cls.MAX_SCORE,
                score,
            ),
        )

    @staticmethod
    def _normalize_string_list(
        value: Any,
    ) -> list[str]:
        """
        Normaliza issues/corrections a listas de strings.
        """

        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            value = value.strip()

            return [value] if value else []

        if not isinstance(
            value,
            (list, tuple),
        ):
            return []

        normalized: list[str] = []

        for item in value:
            if item is None:
                continue

            text = str(
                item,
            ).strip()

            if text:
                normalized.append(
                    text,
                )

        return normalized

    # ==========================================================
    # Standard evaluations
    # ==========================================================

    @classmethod
    def _evaluation_pass(
        cls,
        score: int,
        reason: str,
    ) -> dict[str, Any]:
        """
        Evaluación utilizada cuando SelfCritic no es necesario.
        """

        return {
            "status": "not_required",
            "pass": True,
            "score": score,
            "issues": [],
            "corrections": [],
            "reason": reason,
        }

    @staticmethod
    def _evaluation_from_failure(
        result: ExecutionResult,
    ) -> dict[str, Any]:
        """
        Convierte una ejecución fallida en una evaluación
        determinísticamente fallida.

        No se solicita otro LLM para explicar un fallo
        de ejecución.
        """

        error = result.error or "Ejecución fallida."

        return {
            "status": "execution_failed",
            "pass": False,
            "score": 0,
            "issues": [error],
            "corrections": [],
            "reason": error,
        }

    @staticmethod
    def _evaluation_unavailable(
        reason: str,
    ) -> dict[str, Any]:
        """
        Representa una evaluación que no pudo completarse.

        La ausencia de crítica no equivale a una evaluación
        satisfactoria.
        """

        return {
            "status": "unavailable",
            "pass": None,
            "score": None,
            "issues": [],
            "corrections": [],
            "reason": reason,
        }
