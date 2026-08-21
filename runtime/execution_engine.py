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


class ExecutionEngine:
    """
    Único dueño del lifecycle de ejecución.

    Flujo oficial:

        user input
            → IntentAnalyzer
            → PlanBuilder
            → ExecutionPlan
            → validate
            → context
            → execute
            → evaluate (SelfCritic → EvaluationResult)
            → retry
            → finalize
            → learning

    ExecutionResult es la fuente de verdad del lifecycle.
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_registry: AgentRegistry,
        skill_registry: SkillRegistry,
        context_manager: ContextManager | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
        command_router: Any | None = None,
        capability_guard: CapabilityGuard | None = None,
    ) -> None:
        if agent_registry is None:
            raise ValueError("ExecutionEngine requiere agent_registry.")

        if skill_registry is None:
            raise ValueError("ExecutionEngine requiere skill_registry.")

        self.agent_registry = agent_registry
        self.skill_registry = skill_registry

        self.context_manager = context_manager if context_manager is not None else ContextManager()

        self.intent_analyzer = intent_analyzer if intent_analyzer is not None else IntentAnalyzer()

        self.plan_builder = plan_builder if plan_builder is not None else PlanBuilder()

        self.command_router = command_router

        self.capability_guard = (
            capability_guard if capability_guard is not None else CapabilityGuard()
        )

        self.dispatcher = UnitDispatcher(
            agent_registry=self.agent_registry,
            skill_registry=self.skill_registry,
            capability_guard=self.capability_guard,
        )

        self.metrics: dict[str, int] = {
            "executions": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "cancelled": 0,
            "retries": 0,
        }

        self.critic = SelfCritic()
        self.learner = ContinuousLearner()
        self.engram = EngramMemory()
        self.metrics_store = MetricsStore()
        self.retry_policy = RetryPolicy()
        self._retry_context: dict[str, dict[str, Any]] = {}

        logger.info(
            "ExecutionEngine inicializado | agents=%s | skills=%s",
            self.agent_registry.list(),
            self.skill_registry.list(),
        )

    # =========================================================
    # Public API
    # =========================================================

    def execute_from_input(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        if not user_input or not user_input.strip():
            raise ValueError("user_input no puede estar vacío.")

        logger.info("Engine procesando entrada=%s", user_input[:100])

        if self.command_router is not None:
            try:
                slash_plan = self.command_router.process(user_input)
            except ValueError as exc:
                return ExecutionResult.fail(
                    plan_id="slash",
                    error=str(exc),
                    executor=self.name,
                )

            if slash_plan is not None:
                if metadata:
                    slash_plan.metadata.update(metadata)
                return self.execute(slash_plan)

        intent = self.intent_analyzer.analyze(user_input)
        plan = self.plan_builder.build(intent=intent, original_task=user_input)

        if metadata:
            plan.metadata.update(metadata)

        return self.execute(plan)

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        if plan is None:
            raise ValueError("ExecutionEngine.execute requiere un plan.")

        started_monotonic = time.monotonic()
        started_at = datetime.now(timezone.utc)
        self.metrics["executions"] += 1

        try:
            errors = plan.validate()
            if errors:
                result = self._fail(plan, "; ".join(errors))
                return self._finalize(
                    plan=plan,
                    result=result,
                    started_monotonic=started_monotonic,
                    started_at=started_at,
                )

            plan.mark_validated()

            context = self.context_manager.build(plan) or {}
            # Snapshot inicial (compatibilidad). La fuente de verdad en runtime es `context`.
            plan.loaded_context = dict(context)

            plan.mark_running()

            result = self._execute_with_retries(
                plan,
                context,
                started_at=started_at,
            )

            result = self._finalize(
                plan=plan,
                result=result,
                started_monotonic=started_monotonic,
                started_at=started_at,
            )

            self._learn(plan, result)
            return result

        except Exception as exc:
            logger.exception("Error fatal en ExecutionEngine")
            try:
                plan.mark_failed()
            except Exception:
                logger.exception("No se pudo marcar plan como failed")

            result = self._fail(plan, str(exc))
            return self._finalize(
                plan=plan,
                result=result,
                started_monotonic=started_monotonic,
                started_at=started_at,
            )

    # =========================================================
    # Helpers de estado
    # =========================================================

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

    # =========================================================
    # Finalization
    # =========================================================

    def _finalize(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        started_monotonic: float,
        started_at: datetime,
    ) -> ExecutionResult:
        if not isinstance(result, ExecutionResult):
            result = ExecutionResult.fail(
                plan_id=plan.id,
                error="ExecutionEngine recibió un resultado inválido.",
                executor=self.name,
                started_at=started_at,
            )

        if result.plan_id != plan.id:
            result.plan_id = plan.id

        if result.is_retry:
            result = ExecutionResult.fail(
                plan_id=plan.id,
                error=result.error or "La ejecución terminó en retry inesperadamente.",
                executor=result.executor or self.name,
                retries=result.retries,
                metadata={
                    **dict(result.metadata or {}),
                    "invalid_terminal_retry": True,
                },
                started_at=started_at,
            )

        finished_at = datetime.now(timezone.utc)
        result.set_execution_window(started_at=started_at, finished_at=finished_at)

        self._apply_plan_state(plan, result)

        duration = max(0.0, round(time.monotonic() - started_monotonic, 3))
        result.metadata.update(
            {
                "engine": self.name,
                "duration": duration,
                "plan_id": plan.id,
                "retries": result.retries,
                "terminal": result.is_terminal,
            }
        )

        self._update_metrics(result)
        self._save_metric(plan, result, duration)
        self._retry_context.pop(plan.id, None)

        return result

    def _save_metric(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        duration: float,
    ) -> None:
        try:
            metric = ExecutionMetric(
                execution_id=str(uuid.uuid4()),
                plan_id=plan.id,
                intent=plan.intent or "unknown",
                provider=plan.metadata.get("provider", "unknown"),
                model=plan.metadata.get("model", "unknown"),
                started_at=(result.started_at or datetime.now(timezone.utc)),
                duration=duration,
                status=result.status,
                retry_count=result.retries,
                error=result.error,
                step_count=len(plan.steps),
                metadata=dict(plan.metadata or {}),
            )
            self.metrics_store.save(metric)
        except Exception as exc:
            logger.warning("No se pudo guardar métrica: %s", exc)

    # =========================================================
    # Context
    # =========================================================

    def _store_step_result(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
        result: ExecutionResult,
    ) -> None:
        if not isinstance(result, ExecutionResult):
            raise TypeError("Solo se pueden almacenar ExecutionResult.")
        self.context_manager.record_step_result(context, step, result)

    def _build_step_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
    ) -> dict[str, Any]:
        step_context = dict(context)

        dependencies = self.context_manager.get_dependency_results(context, step)
        if dependencies:
            execution = dict(step_context.get("execution") or {})
            execution["dependencies"] = dependencies
            step_context["execution"] = execution

        self._materialize_dependency_outputs(
            step=step,
            dependencies=dependencies,
            step_context=step_context,
        )

        execution = dict(step_context.get("execution") or {})
        execution["current_step"] = {
            "id": step.id,
            "description": step.description,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "params": dict(step.params or {}),
        }
        step_context["execution"] = execution

        retry_data = self._retry_context.get(plan.id)
        if retry_data:
            step_context["retry_corrections"] = list(retry_data.get("corrections") or [])
            step_context["retry_issues"] = list(retry_data.get("issues") or [])

        return step_context

    # =========================================================
    # Path + materialization
    # =========================================================

    @staticmethod
    def _normalize_write_path(path: str | None, fallback: str = "output.txt") -> str:
        raw = (path or "").strip() or fallback
        p = Path(raw)
        if p.is_absolute():
            raw = p.name or fallback
        raw = raw.replace("\\", "/").lstrip("/")
        parts = [x for x in Path(raw).parts if x not in ("", ".", "..")]
        if not parts:
            parts = [fallback]
        return str(Path(*parts))

    def _materialize_dependency_outputs(
        self,
        step: ExecutionStep,
        dependencies: dict[str, Any],
        step_context: dict[str, Any],
    ) -> None:
        """
        Proyecta outputs tipados de dependencias a:
        - step.params  (Skills, p.ej. write_file)
        - step_context (Agents, p.ej. dependency_text, architecture)
        """
        if not dependencies:
            return

        artifacts: list[dict[str, Any]] = []
        evidence_by_type: dict[str, Any] = {}
        plain_texts: list[str] = []
        analysis_texts: list[str] = []

        for dep_id, dep_data in dependencies.items():
            raw: Any = None

            if isinstance(dep_data, ExecutionResult):
                if not dep_data.is_success:
                    continue
                raw = dep_data.result
            elif isinstance(dep_data, dict):
                status = dep_data.get("status")
                if status is not None and not self._legacy_status_is_success(status):
                    continue
                raw = dep_data.get("result")
                if isinstance(raw, ExecutionResult):
                    if not raw.is_success:
                        continue
                    raw = raw.result
                if isinstance(raw, dict) and "ok" in raw and "result" in raw:
                    if raw.get("ok") is False:
                        continue
                    raw = raw.get("result")
            else:
                continue

            if raw is None:
                continue

            if isinstance(raw, str):
                if raw.strip():
                    plain_texts.append(raw.strip())
                continue

            if not isinstance(raw, dict):
                continue

            payload_type = raw.get("type")

            if payload_type == "code_artifact":
                artifacts.append(raw)
                continue

            if payload_type in {
                "architecture_evidence",
                "quality_evidence",
                "security_evidence",
                "performance_evidence",
                "project_analysis",
            }:
                evidence_by_type[payload_type] = raw
                continue

            # scrape_job / análisis de página
            if payload_type in {
                "job_analysis",
                "page_analysis",
                "scrape_result",
                "landing_analysis",
            }:
                parts: list[str] = []
                title = raw.get("title")
                url = raw.get("url")
                if title:
                    parts.append(f"Título: {title}")
                if url:
                    parts.append(f"URL: {url}")
                body = (
                    raw.get("description")
                    or raw.get("text")
                    or raw.get("content")
                    or raw.get("summary")
                    or ""
                )
                if body:
                    parts.append(str(body).strip())
                pain = raw.get("pain_points")
                if pain:
                    parts.append("Señales: " + ", ".join(str(x) for x in pain))
                if parts:
                    analysis_texts.append("\n".join(parts))
                continue

            if "architecture" in raw and payload_type is None:
                evidence_by_type.setdefault("architecture_evidence", raw)
                continue

            if payload_type is None and ("structure" in raw or "files" in raw or "project" in raw):
                evidence_by_type.setdefault("project_analysis", raw)
                continue

            # dict genérico con texto útil
            for key in ("text", "content", "summary", "analysis", "description"):
                val = raw.get(key)
                if isinstance(val, str) and val.strip():
                    plain_texts.append(val.strip())
                    break

        # -------------------------------------------------
        # write_file
        # -------------------------------------------------
        if step.unit_type == "skill" and step.unit_name == "write_file":
            params = dict(step.params or {})
            planned_path = params.get("path")
            needs_path = not params.get("path")
            needs_content = params.get("content") is None

            if (needs_path or needs_content) and artifacts:
                try:
                    file_index = int(params.get("file_index", 0) or 0)
                except (TypeError, ValueError):
                    file_index = 0
                files = artifacts[0].get("files") or []
                if 0 <= file_index < len(files):
                    chosen = files[file_index] if isinstance(files[file_index], dict) else {}
                    if needs_path and chosen.get("path"):
                        params["path"] = chosen["path"]
                    if needs_content and chosen.get("content") is not None:
                        params["content"] = chosen["content"]

            needs_path = not params.get("path")
            needs_content = params.get("content") is None

            if needs_content and plain_texts:
                text = plain_texts[0]
                content = text
                path_from_json = None
                stripped = text.strip()

                if "code_artifact" in stripped and "{" in stripped:
                    candidate = stripped
                    if candidate.startswith("```"):
                        lines = candidate.split("\n")
                        if lines and lines[0].startswith("```"):
                            lines = lines[:1]
                        if lines and lines[-1].strip().startswith("```"):
                            lines = lines[:-1]
                        candidate = "\n".join(lines).strip()
                    try:
                        data = json.loads(candidate)
                    except json.JSONDecodeError:
                        start = candidate.find("{")
                        end = candidate.rfind("}")
                        data = None
                        if start >= 0 and end > start:
                            try:
                                data = json.loads(candidate[start : end + 1])
                            except json.JSONDecodeError:
                                data = None
                    if isinstance(data, dict) and data.get("type") == "code_artifact":
                        files = data.get("files") or []
                        try:
                            file_index = int(params.get("file_index", 0) or 0)
                        except (TypeError, ValueError):
                            file_index = 0
                        if 0 <= file_index < len(files):
                            chosen = files[file_index]
                            if isinstance(chosen, dict):
                                if chosen.get("content") is not None:
                                    content = chosen["content"]
                                if chosen.get("path"):
                                    path_from_json = chosen["path"]

                params["content"] = content
                if needs_path and not params.get("path"):
                    params["path"] = path_from_json or planned_path or "output.md"

            fallback = planned_path or "output.txt"
            if not isinstance(fallback, str) or not fallback.strip():
                fallback = "output.txt"

            candidate_path = params.get("path") or fallback
            if planned_path and Path(str(candidate_path)).is_absolute():
                candidate_path = planned_path

            params["path"] = self._normalize_write_path(
                str(candidate_path) if candidate_path else None,
                fallback=str(fallback),
            )
            step.params = params

            if params.get("content") is not None:
                logger.info(
                    "Materializado write_file | path=%s | content_len=%s",
                    params.get("path"),
                    len(str(params.get("content") or "")),
                )

        # -------------------------------------------------
        # Agents / contexto
        # -------------------------------------------------
        if artifacts:
            step_context["code_artifacts"] = artifacts

        project_analysis = evidence_by_type.get("project_analysis")
        architecture_evidence = evidence_by_type.get("architecture_evidence")

        if isinstance(project_analysis, dict):
            arch = project_analysis.get("architecture_context")
            if arch and not step_context.get("architecture"):
                step_context["architecture"] = arch
            summary = (
                project_analysis.get("summary") or project_analysis.get("project_summary") or ""
            )
            if summary and not step_context.get("project_summary"):
                step_context["project_summary"] = summary
            step_context["project_analysis"] = {
                "summary": summary,
                "type": project_analysis.get("type", "project_analysis"),
            }

        if isinstance(architecture_evidence, dict) and not step_context.get("architecture"):
            step_context["architecture"] = architecture_evidence

        for key in (
            "quality_evidence",
            "security_evidence",
            "performance_evidence",
        ):
            evidence = evidence_by_type.get(key)
            if isinstance(evidence, dict):
                step_context[key] = evidence

        # Texto de referencia (scrape / analysis / plain)
        if analysis_texts and not step_context.get("dependency_text"):
            step_context["dependency_text"] = analysis_texts[0][:6000]
        elif plain_texts and not step_context.get("dependency_text"):
            if not (architecture_evidence or project_analysis or artifacts):
                step_context["dependency_text"] = plain_texts[0][:6000]

    # =========================================================
    # Timeout helper
    # =========================================================

    def _run_with_timeout(self, fn, timeout: int):
        if timeout <= 0:
            return fn()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeout:
                raise TimeoutError(f"Step excedió el timeout de {timeout}s")

    # =========================================================
    # Retry loop
    # =========================================================

    def _execute_with_retries(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        started_at: datetime,
    ) -> ExecutionResult:
        max_retries = max(0, plan.get_max_retries())
        retries = 0

        try:
            while True:
                logger.info(
                    "Execution intento | plan=%s | retry=%s/%s",
                    plan.id,
                    retries,
                    max_retries,
                )

                # -------------------------------------------------
                # Execute
                # -------------------------------------------------
                if plan.is_multi_step():
                    result = self._execute_steps(plan, context)
                else:
                    result = self._execute_single(plan, context)

                if not isinstance(result, ExecutionResult):
                    raise TypeError("La ejecución debe devolver ExecutionResult.")

                # -------------------------------------------------
                # Evaluate (SelfCritic)
                # -------------------------------------------------
                result = self._evaluate(plan, result, context)

                if not isinstance(result, ExecutionResult):
                    raise TypeError("SelfCritic debe devolver ExecutionResult.")

                result.retries = retries
                result.started_at = started_at

                # -------------------------------------------------
                # Terminal exitoso / parcial / cancelado
                # -------------------------------------------------
                if result.is_success or result.is_partial or result.is_cancelled:
                    return result

                # -------------------------------------------------
                # Reconstruir EvaluationResult desde metadata (si existe)
                # -------------------------------------------------
                evaluation: EvaluationResult | None = None
                raw_eval = (result.metadata or {}).get("evaluation")

                if isinstance(raw_eval, dict):
                    try:
                        evaluation = EvaluationResult(
                            status=raw_eval.get("status", "unavailable"),
                            passed=raw_eval.get("passed"),
                            score=raw_eval.get("score"),
                            issues=list(raw_eval.get("issues") or []),
                            corrections=list(raw_eval.get("corrections") or []),
                            reason=raw_eval.get("reason"),
                            metadata=dict(raw_eval.get("metadata") or {}),
                        )
                    except Exception:
                        evaluation = None

                # -------------------------------------------------
                # Decisión de retry (única autoridad: RetryPolicy)
                # -------------------------------------------------
                decision = self.retry_policy.decide(
                    execution_result=result,
                    evaluation=evaluation,
                    current_retries=retries,
                    max_retries=max_retries,
                )

                result.metadata["retry_decision"] = decision.to_dict()

                if not decision.retry:
                    # Política dice que no se reintenta → terminal failure
                    if result.is_retry or result.is_failure:
                        return ExecutionResult.fail(
                            plan_id=plan.id,
                            error=result.error or decision.reason,
                            executor=result.executor or self.name,
                            retries=retries,
                            metadata={
                                **dict(result.metadata or {}),
                                "retry_decision": decision.to_dict(),
                                "retry_exhausted": retries >= max_retries,
                            },
                            started_at=started_at,
                        )
                    return result

                # -------------------------------------------------
                # Hay que reintentar
                # -------------------------------------------------
                retries += 1
                self.metrics["retries"] += 1

                result.retries = retries
                result.metadata.update(
                    {
                        "retry_count": retries,
                        "max_retries": max_retries,
                        "retry_decision": decision.to_dict(),
                    }
                )

                logger.info(
                    "RetryPolicy decidió reintentar | plan=%s | retry=%s/%s | reason=%s",
                    plan.id,
                    retries,
                    max_retries,
                    decision.reason,
                )

                self._reset_execution_context(plan, context)

                if decision.delay_seconds > 0:
                    time.sleep(decision.delay_seconds)

        finally:
            self._retry_context.pop(plan.id, None)

    def _reset_execution_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        execution = context.setdefault("execution", {})
        if not isinstance(execution, dict):
            execution = {}
            context["execution"] = execution

        completed_steps = execution.get("steps")
        if not isinstance(completed_steps, dict):
            completed_steps = {}
            execution["steps"] = completed_steps

        for step in plan.steps:
            previous = completed_steps.get(step.id)

            if previous is None:
                step.reset()
                completed_steps.pop(step.id, None)
                continue

            if isinstance(previous, ExecutionResult):
                if previous.is_success:
                    continue
                step.reset()
                completed_steps.pop(step.id, None)
                continue

            if isinstance(previous, dict):
                if self._dependency_result_is_success(previous):
                    continue
                step.reset()
                completed_steps.pop(step.id, None)
                continue

            step.reset()
            completed_steps.pop(step.id, None)

        execution["steps"] = completed_steps

    # =========================================================
    # Single / Multi step
    # =========================================================

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

    # =========================================================
    # Analysis → write presentation
    # =========================================================

    def _is_analysis_then_generate_plan(
        self,
        plan: ExecutionPlan,
        executed_steps: list[ExecutionStep],
        results: list[ExecutionResult],
    ) -> bool:
        if len(executed_steps) < 3 or len(results) < 3:
            return False

        units = [(s.unit_type, s.unit_name) for s in executed_steps]
        try:
            analysis_index = units.index(("agent", "task_agent"))
            coder_index = units.index(("agent", "coder"))
            write_index = units.index(("skill", "write_file"))
        except ValueError:
            return False

        return analysis_index < coder_index < write_index

    def _build_analysis_and_write_result(
        self,
        plan: ExecutionPlan,
        executed_steps: list[ExecutionStep],
        results: list[ExecutionResult],
        result_payload: list[dict[str, Any]],
    ) -> dict[str, Any]:
        analysis_text: str | None = None
        absolute_path: str | None = None

        for step, result in zip(executed_steps, results):
            if not result.is_success:
                continue

            if step.unit_type == "agent" and step.unit_name == "task_agent":
                raw = result.result
                if isinstance(raw, str) and raw.strip():
                    analysis_text = raw.strip()
                elif isinstance(raw, dict):
                    candidate = raw.get("result") or raw.get("analysis") or raw.get("content")
                    if candidate is not None:
                        analysis_text = str(candidate).strip()
                    elif raw:
                        analysis_text = str(raw)

            elif step.unit_type == "skill" and step.unit_name == "write_file":
                write_result = result.result
                if isinstance(write_result, dict):
                    absolute_path = write_result.get("absolute_path") or write_result.get("path")

        if analysis_text is None:
            for item in result_payload:
                if (
                    item.get("unit_type") == "agent"
                    and item.get("unit_name") == "task_agent"
                    and item.get("success")
                ):
                    raw = item.get("result")
                    if isinstance(raw, str) and raw.strip():
                        analysis_text = raw.strip()
                        break
                    if isinstance(raw, dict):
                        candidate = raw.get("result") or raw.get("analysis") or raw.get("content")
                        if candidate is not None:
                            analysis_text = str(candidate).strip()
                            break

        if absolute_path is None:
            for item in result_payload:
                if (
                    item.get("unit_type") == "skill"
                    and item.get("unit_name") == "write_file"
                    and item.get("success")
                ):
                    raw = item.get("result")
                    if isinstance(raw, dict):
                        absolute_path = raw.get("absolute_path") or raw.get("path")
                        if absolute_path:
                            break

        return {
            "type": "analysis_and_write",
            "analysis": analysis_text or "(No se pudo recuperar el análisis)",
            "write": {
                "ok": True,
                "path": absolute_path,
                "message": (
                    f"He ejecutado la skill 'write_file' correctamente. "
                    f"El archivo se guardó en: {absolute_path}"
                    if absolute_path
                    else "Archivo escrito correctamente."
                ),
            },
            "summary": (
                "Análisis completado y landing generada correctamente."
                if analysis_text and absolute_path
                else "Proceso completado."
            ),
        }

    # =========================================================
    # Scaffold
    # =========================================================

    def _aggregate_scaffold_results(
        self,
        plan: ExecutionPlan,
        results: list[ExecutionResult],
    ) -> dict[str, Any]:
        modules: list[str] = []
        created: list[str] = []
        adapters: list[str] = []
        errors: list[str] = []
        locale = plan.metadata.get("locale")

        for item in results:
            if item.error:
                errors.append(str(item.error))

            raw = item.result
            if isinstance(raw, dict) and "ok" in raw and "result" in raw:
                if raw.get("ok") is False and raw.get("error"):
                    errors.append(str(raw["error"]))
                raw = raw.get("result")

            if not isinstance(raw, dict):
                continue

            mod = raw.get("module")
            if mod:
                modules.append(str(mod))

            for path in raw.get("created") or []:
                p = str(path)
                created.append(p)
                if "/adapters/" in p.replace("\\", "/"):
                    adapters.append(p)

        def uniq(seq: list[str]) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        return {
            "type": "module_scaffold_batch",
            "modules": uniq(modules),
            "created": uniq(created),
            "adapters": uniq(adapters),
            "locale": locale,
            "from_spec": plan.metadata.get("from_spec"),
            "steps_ok": sum(1 for r in results if r.is_success),
            "steps_total": len(results),
            "errors": errors,
        }

    def _should_aggregate_scaffold(
        self,
        plan: ExecutionPlan,
        results: list[ExecutionResult],
    ) -> bool:
        if len(results) <= 1:
            return False
        if plan.metadata.get("aggregate_results"):
            return True
        intent = (plan.intent or "").lower()
        if intent in {"module_scaffold", "ui_scaffold"}:
            return True
        names = [f"{s.unit_type}:{s.unit_name}" for s in plan.steps]
        scaffoldish = sum(
            1
            for n in names
            if n
            in {
                "skill:scaffold_module",
                "skill:scaffold_ui_shell",
                "skill:write_file",
            }
        )
        return scaffoldish >= 2

    # =========================================================
    # Dependencies
    # =========================================================

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

    # =========================================================
    # Evaluation
    # =========================================================

    def _evaluate(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        if not (result.is_success or result.is_partial):
            return result

        if not plan.metadata.get("requires_self_critic", False):
            return result

        evaluation: EvaluationResult = self.critic.evaluate(
            plan=plan,
            result=result,
            context=context or {},
        )

        result.metadata["evaluation"] = evaluation.to_dict()

        try:
            self.engram.save(
                f"SelfCritic: {plan.id} - score={evaluation.score}",
                tags=[
                    "self_critic",
                    f"plan_{plan.id}",
                    f"score_{evaluation.score}",
                ],
            )
        except Exception:
            logger.debug("No se pudo persistir SelfCritic en EngramMemory.", exc_info=True)

        if evaluation.is_passed or evaluation.is_skipped or evaluation.is_unavailable:
            return result

        self._retry_context[plan.id] = {
            "corrections": evaluation.corrections,
            "issues": evaluation.issues,
        }

        return ExecutionResult.retry(
            plan_id=plan.id,
            error=evaluation.reason or "Evaluación fallida",
            retries=result.retries,
            executor="self_critic",
            metadata={
                **dict(result.metadata or {}),
                "evaluation": evaluation.to_dict(),
                "corrections": evaluation.corrections,
                "issues": evaluation.issues,
            },
            started_at=result.started_at,
        )

    # =========================================================
    # Learning / Ordering / State / Metrics
    # =========================================================

    def _learn(self, plan: ExecutionPlan, result: ExecutionResult) -> None:
        if not (result.is_success or result.is_partial):
            return
        try:
            proposed = self.learner.extract_and_learn(
                user_query=plan.original_task,
                assistant_response=str(result.result or result.error or ""),
            )
            if proposed:
                logger.info(
                    "Learning candidate creado | plan=%s | task=%s",
                    plan.id,
                    (plan.original_task or "")[:80],
                )
        except Exception as exc:
            logger.warning("Learning post-ejecución falló: %s", exc)

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

    def _apply_plan_state(self, plan: ExecutionPlan, result: ExecutionResult) -> None:
        if result.is_success:
            plan.mark_completed()
        elif result.is_partial:
            plan.mark_partial()
        elif result.is_failure:
            plan.mark_failed()
        elif result.is_cancelled:
            plan.mark_cancelled()
        elif result.is_retry:
            logger.error("Intento de finalizar plan en retry | plan=%s", plan.id)

    def _update_metrics(self, result: ExecutionResult) -> None:
        if result.is_success:
            self.metrics["success"] += 1
        elif result.is_partial:
            self.metrics["partial"] += 1
        elif result.is_failure:
            self.metrics["failed"] += 1
        elif result.is_cancelled:
            self.metrics["cancelled"] += 1

    def get_metrics(self) -> dict[str, int]:
        return dict(self.metrics)

    def _fail(self, plan: ExecutionPlan, error: str) -> ExecutionResult:
        logger.error("Plan %s falló: %s", plan.id, error)
        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )
