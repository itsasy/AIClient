from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from agents.manager import AgentManager
from core.analytics.metrics_store import MetricsStore
from core.analytics.models import ExecutionMetric
from core.context.manager import ContextManager
from core.engram_memory import EngramMemory
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.intent import IntentAnalyzer
from core.learner import ContinuousLearner
from core.planning import PlanBuilder
from core.self_critic import SelfCritic
from runtime.dispatcher import UnitDispatcher
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Único dueño del lifecycle de ejecución.

    Flujo oficial:

        user input
            ↓
        IntentAnalyzer
            ↓
        IntentResult
            ↓
        PlanBuilder
            ↓
        ExecutionPlan
            ↓
        validate
            ↓
        context
            ↓
        execute
            ↓
        evaluate
            ↓
        retry
            ↓
        finalize
            ↓
        ExecutionResult
            ↓
        learning
            ↓
        metrics

    El Engine coordina la ejecución.

    No:
        - Descubre Agents.
        - Descubre Skills.
        - Decide qué Agent/Skill utilizar.
        - Registra unidades.
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
        skill_manager: SkillManager | None = None,
        context_manager: ContextManager | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
    ) -> None:
        self.context_manager = context_manager or ContextManager()
        self.intent_analyzer = intent_analyzer or IntentAnalyzer()
        self.plan_builder = plan_builder or PlanBuilder()
        self.agent_manager = agent_manager or AgentManager()
        self.skill_manager = skill_manager or SkillManager()

        self.dispatcher = UnitDispatcher(
            agent_registry=self.agent_manager.registry,
            skill_registry=self.skill_manager.registry,
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

        self._retry_context: dict[str, dict[str, Any]] = {}

        logger.info(
            "ExecutionEngine inicializado | agents=%s | skills=%s",
            self.agent_manager.list(),
            self.skill_manager.list(),
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

        intent = self.intent_analyzer.analyze(user_input)

        plan = self.plan_builder.build(
            intent=intent,
            original_task=user_input,
        )

        if metadata:
            plan.metadata.update(metadata)

        return self.execute(plan)

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        started = time.monotonic()
        self.metrics["executions"] += 1

        try:
            errors = plan.validate()
            if errors:
                result = self._fail(plan, "; ".join(errors))
                return self._finalize(plan, result, started)

            plan.mark_validated()

            context = self.context_manager.build(plan) or {}
            plan.loaded_context = dict(context)

            plan.mark_running()

            result = self._execute_with_retries(plan, context)
            result = self._finalize(plan, result, started)
            self._learn(plan, result)

            return result

        except Exception as exc:
            logger.exception("Error fatal en ExecutionEngine")

            try:
                plan.mark_failed()
            except Exception:
                logger.exception("No se pudo marcar plan como failed")

            result = self._fail(plan, str(exc))
            return self._finalize(plan, result, started)

    # =========================================================
    # Finalization
    # =========================================================

    def _finalize(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        started: float,
    ) -> ExecutionResult:
        self._apply_plan_state(plan, result)

        duration = round(time.monotonic() - started, 3)

        result.metadata.update(
            {
                "engine": self.name,
                "duration": duration,
                "plan_id": plan.id,
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
                started_at=datetime.now(timezone.utc),
                duration=duration,
                status=result.status,
                retry_count=getattr(result, "retries", 0) or 0,
                error=result.error,
                step_count=len(plan.steps),
                metadata=dict(plan.metadata or {}),
            )
            self.metrics_store.save(metric)
        except Exception as exc:
            logger.warning("No se pudo guardar métrica: %s", exc)

    # =========================================================
    # Execution context
    # =========================================================

    def _store_step_result(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
        result: ExecutionResult,
    ) -> None:
        self.context_manager.record_step_result(context, step, result)

    def _build_step_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
    ) -> dict[str, Any]:
        step_context = dict(context)

        dependencies = self.context_manager.get_dependency_results(
            context,
            step,
        )

        if dependencies:
            execution = step_context.setdefault("execution", {})
            execution["dependencies"] = dependencies

        # Puente Agent → Skill / evidence → Agent
        self._materialize_dependency_outputs(
            step=step,
            dependencies=dependencies,
            step_context=step_context,
        )

        execution = step_context.setdefault("execution", {})
        execution["current_step"] = {
            "id": step.id,
            "description": step.description,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "params": dict(step.params or {}),
        }

        retry_data = self._retry_context.get(plan.id)
        if retry_data:
            step_context["retry_corrections"] = retry_data.get("corrections", [])
            step_context["retry_issues"] = retry_data.get("issues", [])

        return step_context

    def _materialize_dependency_outputs(
        self,
        step: ExecutionStep,
        dependencies: dict[str, Any],
        step_context: dict[str, Any],
    ) -> None:
        """
        Traduce resultados tipados de dependencias a:
          - step.params   (para Skills)
          - step_context  (para Agents)

        No inventa contenido. Solo proyecta lo que ya produjo
        un step anterior. El plan sigue siendo la fuente de verdad.
        """
        if not dependencies:
            return

        artifacts: list[dict[str, Any]] = []
        evidence_by_type: dict[str, Any] = {}

        for _dep_id, dep_data in dependencies.items():
            if not isinstance(dep_data, dict):
                continue

            status = dep_data.get("status")
            raw = dep_data.get("result")

            # Solo dependencias exitosas (tolerante a status None)
            if status and status not in ("completed", "success"):
                if not raw:
                    continue

            if raw is None:
                continue

            payload = raw
            if isinstance(raw, dict) and "result" in raw and "ok" in raw:
                if not raw.get("ok", True):
                    continue
                payload = raw.get("result")

            if not isinstance(payload, dict):
                continue

            payload_type = payload.get("type")

            if payload_type == "code_artifact":
                artifacts.append(payload)
            elif payload_type in (
                "architecture_evidence",
                "quality_evidence",
                "security_evidence",
                "performance_evidence",
                "project_analysis",
            ):
                evidence_by_type[payload_type] = payload
            elif "architecture" in payload and payload_type is None:
                evidence_by_type["architecture_evidence"] = payload

            # analyze_project puede devolver snapshot sin type
            if payload_type is None and (
                "files" in payload or "structure" in payload or "summary" in payload
            ):
                evidence_by_type.setdefault("project_analysis", payload)

        # Skills: materializar en step.params (sin sobrescribir)
        if step.unit_type == "skill" and step.unit_name == "write_file":
            params = dict(step.params or {})
            needs_path = not params.get("path")
            needs_content = params.get("content") is None

            if (needs_path or needs_content) and artifacts:
                file_index = int(params.get("file_index", 0) or 0)
                files = artifacts[0].get("files") or []

                if 0 <= file_index < len(files):
                    chosen = files[file_index]
                    if needs_path and chosen.get("path"):
                        params["path"] = chosen["path"]
                    if needs_content and chosen.get("content") is not None:
                        params["content"] = chosen["content"]

                    step.params = params

                    current = step_context.setdefault("execution", {})
                    current_step = current.setdefault("current_step", {})
                    current_step["params"] = dict(params)

        # Agents: materializar evidencia en contexto de primer nivel
        if step.unit_type == "agent":
            if "architecture_evidence" in evidence_by_type:
                evidence = evidence_by_type["architecture_evidence"]
                step_context["architecture"] = evidence
                step_context["project_summary"] = evidence.get("summary", "")

            if "project_analysis" in evidence_by_type:
                analysis = evidence_by_type["project_analysis"]
                step_context["project_analysis"] = analysis
                # ArchitectAgent también mira "architecture"
                if "architecture" not in step_context:
                    step_context["architecture"] = analysis
                if not step_context.get("project_summary"):
                    step_context["project_summary"] = (
                        analysis.get("summary", "") if isinstance(analysis, dict) else ""
                    )

            for key in (
                "quality_evidence",
                "security_evidence",
                "performance_evidence",
            ):
                if key in evidence_by_type:
                    step_context[key] = evidence_by_type[key]

            if artifacts:
                step_context["code_artifacts"] = artifacts

    # =========================================================
    # Retry
    # =========================================================

    def _execute_with_retries(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:
        max_retries = plan.get_max_retries()
        retries = 0

        try:
            while True:
                if plan.is_multi_step():
                    result = self._execute_steps(plan, context)
                else:
                    result = self._execute_single(plan, context)

                result = self._evaluate(plan, result)

                if result.is_success or result.is_partial:
                    return result

                if result.is_cancelled:
                    return result

                if not (result.is_failure or result.status == "retry"):
                    return result

                if retries >= max_retries:
                    return result

                retries += 1
                self.metrics["retries"] += 1
                result.metadata["retry_count"] = retries

                logger.info(
                    "Retry plan=%s intento=%s/%s",
                    plan.id,
                    retries,
                    max_retries,
                )

                self._reset_execution_context(plan, context)
                time.sleep(0.5)

        finally:
            self._retry_context.pop(plan.id, None)

    def _reset_execution_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        execution = context.setdefault("execution", {})
        execution["steps"] = {}
        for step in plan.steps:
            step.reset()

    # =========================================================
    # Single execution
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

        try:
            result = self.dispatcher.dispatch(plan, step, step_context)
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
                },
            )

        self._store_step_result(plan, context, step, result)
        return result

    # =========================================================
    # Multi-step execution
    # =========================================================

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

            try:
                result = self.dispatcher.dispatch(plan, step, step_context)
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
                    },
                )

            self._store_step_result(plan, context, step, result)
            results.append(result)
            executed_steps.append(step)

            if result.is_failure:
                error = result.error or "Error desconocido"
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": error,
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
                "status": step.status,
                "result": result.result,
                "error": result.error,
            }
            for step, result in zip(executed_steps, results)
        ]

        if not errors:
            final_result = results[-1].result if results else None
            return ExecutionResult.success(
                plan_id=plan.id,
                result=final_result,
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                },
            )

        detail = "\n".join(
            f"- {error['step']} ({error['unit']}): {error['error']}" for error in errors
        )

        if len(errors) == len(results):
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
        completed_steps = execution.get("steps", {})

        for dependency_id in step.depends_on:
            dependency = completed_steps.get(dependency_id)

            if dependency is None:
                return f"Dependencia no ejecutada: {dependency_id}"

            status = dependency.get("status")
            if status not in ("completed", "success"):
                return f"Dependencia fallida: {dependency_id}"

        return None

    # =========================================================
    # Evaluation
    # =========================================================

    def _evaluate(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> ExecutionResult:
        if not plan.metadata.get("requires_self_critic", False):
            return result

        if result.is_failure:
            return result

        evaluation = self.critic.evaluate(plan, result)
        result.metadata["evaluation"] = evaluation

        try:
            self.engram.save(
                f"SelfCritic: {plan.id} - score={evaluation.get('score')}",
                tags=[
                    "self_critic",
                    f"plan_{plan.id}",
                    f"score_{evaluation.get('score', 0)}",
                ],
            )
        except Exception:
            pass

        if evaluation.get("pass", True):
            return result

        corrections = evaluation.get("corrections", [])
        self._retry_context[plan.id] = {
            "corrections": corrections,
            "issues": evaluation.get("issues", []),
        }

        return ExecutionResult.retry(
            plan_id=plan.id,
            error=evaluation.get("reason", "Evaluación fallida"),
            retries=getattr(result, "retries", 0) + 1,
            executor="self_critic",
            metadata={
                "evaluation": evaluation,
                "corrections": corrections,
            },
        )

    # =========================================================
    # Learning
    # =========================================================

    def _learn(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        if not (result.is_success or result.is_partial):
            return

        try:
            self.learner.extract_and_learn(
                user_query=plan.original_task,
                assistant_response=str(result.result or result.error or ""),
            )
        except Exception as exc:
            logger.warning("Learning post-ejecución falló: %s", exc)

    # =========================================================
    # Ordering
    # =========================================================

    def _resolve_order(
        self,
        steps: list[ExecutionStep],
    ) -> list[ExecutionStep]:
        ordered: list[ExecutionStep] = []
        resolved: set[str] = set()
        pending = list(steps)
        available_ids = {step.id for step in steps}

        while pending:
            progress = False

            for step in pending[:]:
                missing = [dep for dep in step.depends_on if dep not in available_ids]
                if missing:
                    raise ValueError(f"Dependencias inexistentes: {missing}")

                if all(dep in resolved for dep in step.depends_on):
                    ordered.append(step)
                    resolved.add(step.id)
                    pending.remove(step)
                    progress = True

            if not progress:
                raise RuntimeError("Dependencias circulares en el plan.")

        return ordered

    # =========================================================
    # Plan state
    # =========================================================

    def _apply_plan_state(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        if result.is_success:
            plan.mark_completed()
        elif result.is_partial:
            plan.mark_partial()
        elif result.is_failure:
            plan.mark_failed()
        elif result.is_cancelled:
            plan.mark_cancelled()

    # =========================================================
    # Metrics
    # =========================================================

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

    # =========================================================
    # Failure
    # =========================================================

    def _fail(self, plan: ExecutionPlan, error: str) -> ExecutionResult:
        logger.error("Plan %s falló: %s", plan.id, error)
        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )
