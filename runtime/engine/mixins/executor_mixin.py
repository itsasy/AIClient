from __future__ import annotations
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.analytics.metrics_store import MetricsStore
from core.analytics.models import ExecutionMetric
from core.context.manager import ContextManager
from core.engram_memory import EngramMemory
from core.evaluation_result import EvaluationResult
from core.retry_policy import RetryPolicy
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.intent import IntentAnalyzer
from core.learner import ContinuousLearner
from core.planning import PlanBuilder
from core.self_critic import SelfCritic
from runtime.dispatcher import UnitDispatcher
from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry
from core.governance.capability_guard import CapabilityGuard

logger = logging.getLogger(__name__)

class EngineExecutorMixin:
    @staticmethod
    def _legacy_status_is_success(value: Any) -> bool:
        return value in {"completed", "success", "ok"}

    @classmethod
    def _dependency_result_is_success(cls, value: Any) -> bool:
        if isinstance(value, ExecutionResult):
            return value.is_success

        if isinstance(value, dict):
            status = value.get("status")
            if cls._legacy_status_is_success(status):
                return True

            raw = value.get("result")
            if isinstance(raw, ExecutionResult):
                return raw.is_success
            if isinstance(raw, dict) and "ok" in raw:
                return bool(raw.get("ok"))

        return False

    def _run_with_timeout(self, fn, timeout: int):
        if timeout <= 0:
            return fn()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeout:
                raise TimeoutError(f"Step excedió el timeout de {timeout}s")

    def _execute_single(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:
        if not plan.execution_unit_type:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error="Plan sin execution_unit_type.",
                executor=self.name,
            )
        if not plan.execution_unit:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error="Plan sin execution_unit.",
                executor=self.name,
            )

        step = ExecutionStep(
            description=(plan.objective or plan.original_task),
            unit_type=plan.execution_unit_type,
            unit_name=plan.execution_unit,
            params=dict(plan.params or {}),
        )

        step_context = self._build_step_context(plan, context, step)
        step.mark_running()

        step_timeout = getattr(step, "timeout", 120) or 120

        try:
            result = self._run_with_timeout(
                lambda: self.dispatcher.dispatch(plan, step, step_context),
                timeout=step_timeout,
            )
            if not isinstance(result, ExecutionResult):
                raise TypeError("UnitDispatcher.dispatch debe devolver ExecutionResult.")

            step.apply_result(
                result=result.result,
                success=result.is_success,
                error=result.error,
            )
        except Exception as exc:
            step.mark_failed(str(exc))
            result = ExecutionResult.fail(
                plan_id=plan.id,
                error=str(exc),
                executor=self.name,
                metadata={
                    "step_id": step.id,
                    "step": step.description,
                    "unit": step.unit_name,
                    "timeout": isinstance(exc, TimeoutError),
                },
            )

        self._store_step_result(plan, context, step, result)
        return result

    def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:
        if not plan.steps:
            return self._fail(plan, "Plan multi_step sin pasos.")

        ordered = self._resolve_order(plan.steps)
        results: list[ExecutionResult] = []
        executed_steps: list[ExecutionStep] = []
        errors: list[dict[str, str]] = []

        for step in ordered:
            previous = context.get("execution", {}).get("steps", {}).get(step.id)

            if previous is not None:
                if isinstance(previous, ExecutionResult) and previous.is_success:
                    results.append(previous)
                    executed_steps.append(step)
                    continue
                if isinstance(previous, dict) and self._dependency_result_is_success(previous):
                    continue

            dependency_failure = self._dependency_failure(step, context)
            if dependency_failure is not None:
                step.mark_skipped(dependency_failure)
                result = ExecutionResult.fail(
                    plan_id=plan.id,
                    error=dependency_failure,
                    executor=self.name,
                    metadata={
                        "step_id": step.id,
                        "step": step.description,
                        "unit": step.unit_name,
                        "skipped": True,
                    },
                )
                self._store_step_result(plan, context, step, result)
                results.append(result)
                executed_steps.append(step)
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": dependency_failure,
                    }
                )
                if plan.should_stop_on_error():
                    break
                continue

            step_context = self._build_step_context(plan, context, step)
            step.mark_running()
            step_timeout = getattr(step, "timeout", 120) or 120

            try:
                result = self._run_with_timeout(
                    lambda: self.dispatcher.dispatch(plan, step, step_context),
                    timeout=step_timeout,
                )
                if not isinstance(result, ExecutionResult):
                    raise TypeError("UnitDispatcher.dispatch debe devolver ExecutionResult.")

                step.apply_result(
                    result=result.result,
                    success=result.is_success,
                    error=result.error,
                )
            except Exception as exc:
                step.mark_failed(str(exc))
                result = ExecutionResult.fail(
                    plan_id=plan.id,
                    error=str(exc),
                    executor=self.name,
                    metadata={
                        "step_id": step.id,
                        "step": step.description,
                        "unit": step.unit_name,
                        "timeout": isinstance(exc, TimeoutError),
                    },
                )

            self._store_step_result(plan, context, step, result)
            results.append(result)
            executed_steps.append(step)

            if result.is_retry:
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": result.error or "El step solicitó un reintento.",
                    }
                )
                if plan.should_stop_on_error():
                    break
            elif result.is_failure:
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": result.error or "Error desconocido",
                    }
                )
                if plan.should_stop_on_error():
                    break
            elif result.is_cancelled:
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": result.error or "Step cancelado.",
                    }
                )
                if plan.should_stop_on_error():
                    break

        result_payload = [
            {
                "step_id": step.id,
                "description": step.description,
                "unit_type": step.unit_type,
                "unit_name": step.unit_name,
                "status": result.status,
                "result": result.result,
                "error": result.error,
                "success": result.is_success,
                "partial": result.is_partial,
                "failure": result.is_failure,
                "retry": result.is_retry,
                "cancelled": result.is_cancelled,
                "terminal": result.is_terminal,
            }
            for step, result in zip(executed_steps, results)
        ]

        if any(r.is_retry for r in results):
            detail = "\n".join(f"- {e['step']} ({e['unit']}): {e['error']}" for e in errors)
            return ExecutionResult.retry(
                plan_id=plan.id,
                error=detail or "Uno o más steps solicitaron un reintento.",
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                    "retry_requested": True,
                },
            )

        if any(r.is_cancelled for r in results):
            detail = "\n".join(f"- {e['step']} ({e['unit']}): {e['error']}" for e in errors)
            return ExecutionResult.cancelled(
                plan_id=plan.id,
                error=detail or "Uno o más steps fueron cancelados.",
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                },
            )

        if not errors:
            if self._is_analysis_then_generate_plan(plan, executed_steps, results):
                final_result = self._build_analysis_and_write_result(
                    plan=plan,
                    executed_steps=executed_steps,
                    results=results,
                    result_payload=result_payload,
                )
                return ExecutionResult.success(
                    plan_id=plan.id,
                    result=final_result,
                    executor=self.name,
                    metadata={
                        "steps": result_payload,
                        "step_count": len(results),
                        "presentation": "analysis_then_write",
                    },
                )

            if self._should_aggregate_scaffold(plan, results):
                final_result = self._aggregate_scaffold_results(plan, results)
            else:
                final_result = results[-1].result if results else None

            return ExecutionResult.success(
                plan_id=plan.id,
                result=final_result,
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                    "aggregated": (
                        isinstance(final_result, dict)
                        and final_result.get("type") == "module_scaffold_batch"
                    ),
                },
            )

        detail = "\n".join(f"- {e['step']} ({e['unit']}): {e['error']}" for e in errors)

        if len(errors) == len(results) and results:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=detail,
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                },
            )

        return ExecutionResult.partial(
            plan_id=plan.id,
            result=(results[-1].result if results else None),
            error=detail,
            executor=self.name,
            metadata={
                "steps": result_payload,
                "step_count": len(results),
            },
        )

    def _dependency_failure(
        self,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> str | None:
        if not step.depends_on:
            return None

        execution = context.get("execution", {})
        if not isinstance(execution, dict):
            return "Contexto de ejecución inválido para resolver dependencias."

        completed_steps = execution.get("steps", {})
        if not isinstance(completed_steps, dict):
            return "Contexto de steps inválido para resolver dependencias."

        for dependency_id in step.depends_on:
            dependency = completed_steps.get(dependency_id)
            if dependency is None:
                return f"Dependencia no ejecutada: {dependency_id}"

            if isinstance(dependency, ExecutionResult):
                if dependency.is_success:
                    continue
                if dependency.error:
                    return (
                        f"Dependencia fallida: {dependency_id} "
                        f"(status={dependency.status}): {dependency.error}"
                    )
                return f"Dependencia no válida: {dependency_id} (status={dependency.status})"

            if isinstance(dependency, dict):
                if self._dependency_result_is_success(dependency):
                    continue
                error = dependency.get("error")
                if error:
                    return (
                        f"Dependencia fallida: {dependency_id} "
                        f"(status={dependency.get('status')}): {error}"
                    )
                return (
                    f"Dependencia no válida: {dependency_id} "
                    f"(status={dependency.get('status')})"
                )

            return f"Dependencia inválida: {dependency_id}"

        return None

    def _resolve_order(self, steps: list[ExecutionStep]) -> list[ExecutionStep]:
        ids = [s.id for s in steps]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for step in steps:
            if step.id in seen:
                duplicates.add(step.id)
            seen.add(step.id)
        if duplicates:
            raise ValueError(f"IDs de steps duplicados: {sorted(duplicates)}")

        ordered: list[ExecutionStep] = []
        resolved: set[str] = set()
        pending = list(steps)
        available_ids = set(ids)

        while pending:
            progress = False
            for step in pending[:]:
                missing = [d for d in step.depends_on if d not in available_ids]
                if missing:
                    raise ValueError(f"Dependencias inexistentes: {missing}")
                if all(d in resolved for d in step.depends_on):
                    ordered.append(step)
                    resolved.add(step.id)
                    pending.remove(step)
                    progress = True
            if not progress:
                raise RuntimeError("Dependencias circulares en el plan.")
        return ordered

