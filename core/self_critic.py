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
    """

    DEFAULT_SCORE = 5

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
    ) -> dict[str, Any]:
        """
        Evalúa el resultado de una ejecución.
        """

        # ------------------------------------------------------
        # Resultado fallido
        # ------------------------------------------------------

        if result.is_failure:
            return self._evaluation_from_failure(result)

        # ------------------------------------------------------
        # Self-critic no requerido
        # ------------------------------------------------------

        if not plan.metadata.get(
            "requires_self_critic",
            False,
        ):
            return self._evaluation_pass(
                score=10,
                reason="No se requirió crítica.",
            )

        # ------------------------------------------------------
        # Construcción del contexto
        # ------------------------------------------------------

        context = self._build_context(
            plan=plan,
            result=result,
        )

        try:
            prompt = self.prompt_builder.build(
                plan=plan,
                context=context,
                prompt_type=PromptType.CRITIQUE,
            )

            response = LLMRouter.generate(
                plan=plan,
                context={
                    "prompt": prompt,
                    "prompt_type": PromptType.CRITIQUE.value,
                },
            )

            return self._parse_and_validate(response)

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
    ) -> dict[str, Any]:

        context: dict[str, Any] = {
            "execution": {
                "plan_id": plan.id,
                "task": plan.original_task,
                "result": result.to_dict(),
            }
        }

        # Contexto cargado durante la ejecución.
        #
        # Esto permite que el crítico evalúe el resultado
        # respecto a la evidencia que recibió la ejecución.
        loaded_context = getattr(
            plan,
            "loaded_context",
            None,
        )

        if isinstance(loaded_context, dict):
            for key in (
                "architecture",
                "project_analysis",
                "standards",
                "gentleman",
                "swarmforge",
                "engram",
                "project_summary",
            ):
                if key in loaded_context:
                    context[key] = loaded_context[key]

        return context

    # ==========================================================
    # Parsing
    # ==========================================================

    def _parse_and_validate(
        self,
        response: str,
    ) -> dict[str, Any]:

        if not response or not response.strip():
            return self._evaluation_unavailable(
                reason="El LLM no devolvió una respuesta.",
            )

        data = self._extract_json(response)

        if data is None:
            return self._evaluation_unavailable(
                reason="La respuesta del LLM no contiene JSON válido.",
            )

        return self._normalize_evaluation(data)

    def _extract_json(
        self,
        response: str,
    ) -> dict[str, Any] | None:

        text = response.strip()

        # Caso ideal: respuesta completamente JSON.
        try:
            parsed = json.loads(text)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

        # Fallback para respuestas que contienen texto
        # alrededor del JSON.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            return None

        candidate = text[start : end + 1]

        try:
            parsed = json.loads(candidate)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            logger.warning("SelfCritic recibió JSON inválido.")

        return None

    # ==========================================================
    # Validation / normalization
    # ==========================================================

    def _normalize_evaluation(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        raw_pass = data.get("pass")
        raw_score = data.get("score")
        raw_issues = data.get("issues")
        raw_corrections = data.get("corrections")
        raw_reason = data.get("reason")

        # ------------------------------------------------------
        # Score
        # ------------------------------------------------------

        score = self._normalize_score(raw_score)

        # ------------------------------------------------------
        # Pass
        # ------------------------------------------------------

        if isinstance(raw_pass, bool):
            passed = raw_pass
        else:
            passed = score >= 5

        # La puntuación es la fuente de coherencia.
        passed = score >= 5 if raw_pass is None else passed

        # ------------------------------------------------------
        # Lists
        # ------------------------------------------------------

        issues = self._normalize_string_list(raw_issues)

        corrections = self._normalize_string_list(raw_corrections)

        # ------------------------------------------------------
        # Reason
        # ------------------------------------------------------

        reason = str(raw_reason).strip() if raw_reason is not None else ""

        # ------------------------------------------------------
        # Contract
        # ------------------------------------------------------

        return {
            "status": "completed",
            "pass": passed,
            "score": score,
            "issues": issues,
            "corrections": corrections,
            "reason": reason,
        }

    @staticmethod
    def _normalize_score(
        value: Any,
    ) -> int:

        try:
            score = int(value)
        except (TypeError, ValueError):
            score = SelfCritic.DEFAULT_SCORE

        return max(
            0,
            min(
                10,
                score,
            ),
        )

    @staticmethod
    def _normalize_string_list(
        value: Any,
    ) -> list[str]:

        if value is None:
            return []

        if isinstance(value, str):
            return [value.strip()] if value.strip() else []

        if not isinstance(value, list):
            return []

        return [str(item).strip() for item in value if str(item).strip()]

    # ==========================================================
    # Standard evaluations
    # ==========================================================

    @staticmethod
    def _evaluation_pass(
        score: int,
        reason: str,
    ) -> dict[str, Any]:

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

        return {
            "status": "unavailable",
            "pass": None,
            "score": None,
            "issues": [],
            "corrections": [],
            "reason": reason,
        }
