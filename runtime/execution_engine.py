from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from agents.manager import AgentManager
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
from core.analytics.metrics_store import MetricsStore

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

        self._retry_context: dict[
            str,
            dict[str, Any],
        ] = {}

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

        logger.info(
            "Engine procesando entrada=%s",
            user_input[:100],
        )

        intent = self.intent_analyzer.analyze(user_input)

        plan = self.plan_builder.build(
            intent=intent,
            original_task=user_input,
        )

        if metadata:
            plan.metadata.update(metadata)

        return self.execute(plan)

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        started = time.monotonic()

        self.metrics["executions"] += 1

        try:
            # =================================================
            # 1. Validate
            # =================================================

            errors = plan.validate()

            if errors:
                result = self._fail(
                    plan,
                    "; ".join(errors),
                )

                return self._finalize(
                    plan,
                    result,
                    started,
                )

            plan.mark_validated()

            # =================================================
            # 2. Context
            # =================================================

            context = self.context_manager.build(plan) or {}

            plan.loaded_context = dict(context)

            # =================================================
            # 3. Running
            # =================================================

            plan.mark_running()

            # =================================================
            # 4. Execute / Evaluate / Retry
            # =================================================

            result = self._execute_with_retries(
                plan,
                context,
            )

            # =================================================
            # 5. Finalize
            # =================================================

            result = self._finalize(
                plan,
                result,
                started,
            )

            # =================================================
            # 6. Learning
            # =================================================

            self._learn(
                plan,
                result,
            )

            return result

        except Exception as exc:
            logger.exception("Error fatal en ExecutionEngine")

            try:
                plan.mark_failed()
            except Exception:
                logger.exception("No se pudo marcar plan como failed")

            result = self._fail(
                plan,
                str(exc),
            )

            return self._finalize(
                plan,
                result,
                started,
            )

    # =========================================================
    # Finalization
    # =========================================================

    def _finalize(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        started: float,
    ) -> ExecutionResult:

        self._apply_plan_state(
            plan,
            result,
        )

        duration = round(
            time.monotonic() - started,
            3,
        )

        result.metadata.update(
            {
                "engine": self.name,
                "duration": duration,
                "plan_id": plan.id,
            }
        )

        self._update_metrics(result)

        self._save_metric(
            plan,
            result,
            duration,
        )

        self._retry_context.pop(
            plan.id,
            None,
        )

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
                provider=plan.metadata.get(
                    "provider",
                    "unknown",
                ),
                model=plan.metadata.get(
                    "model",
                    "unknown",
                ),
                started_at=datetime.now(timezone.utc),
                duration=duration,
                status=result.status,
                retry_count=result.retries,
                error=result.error,
                step_count=len(plan.steps),
                metadata=plan.metadata,
            )

            self.metrics_store.save(metric)

        except Exception as exc:
            logger.warning(
                "No se pudo guardar métrica: %s",
                exc,
            )

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

        self.context_manager.record_step_result(
            context,
            step,
            result,
        )

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
            execution = step_context.setdefault(
                "execution",
                {},
            )

            execution["dependencies"] = dependencies

        execution = step_context.setdefault(
            "execution",
            {},
        )

        execution["current_step"] = {
            "id": step.id,
            "description": step.description,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "params": dict(step.params),
        }

        retry_data = self._retry_context.get(plan.id)

        if retry_data:
            step_context["retry_corrections"] = retry_data.get(
                "corrections",
                [],
            )

            step_context["retry_issues"] = retry_data.get(
                "issues",
                [],
            )

        return step_context

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
                    result = self._execute_steps(
                        plan,
                        context,
                    )
                else:
                    result = self._execute_single(
                        plan,
                        context,
                    )

                result = self._evaluate(
                    plan,
                    result,
                )

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

                self._reset_execution_context(
                    plan,
                    context,
                )

                time.sleep(0.5)

        finally:
            self._retry_context.pop(
                plan.id,
                None,
            )

    def _reset_execution_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:

        execution = context.setdefault(
            "execution",
            {},
        )

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

        step_context = self._build_step_context(
            plan,
            context,
            step,
        )

        step.mark_running()

        try:
            result = self.dispatcher.dispatch(
                plan,
                step,
                step_context,
            )

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

        self._store_step_result(
            plan,
            context,
            step,
            result,
        )

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
            return self._fail(
                plan,
                "Plan multi_step sin pasos.",
            )

        ordered = self._resolve_order(plan.steps)

        results: list[ExecutionResult] = []
        executed_steps: list[ExecutionStep] = []
        errors: list[dict[str, str]] = []

        for step in ordered:

            dependency_failure = self._dependency_failure(
                step,
                context,
            )

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

                self._store_step_result(
                    plan,
                    context,
                    step,
                    result,
                )

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

            step_context = self._build_step_context(
                plan,
                context,
                step,
            )

            step.mark_running()

            try:
                result = self.dispatcher.dispatch(
                    plan,
                    step,
                    step_context,
                )

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

            self._store_step_result(
                plan,
                context,
                step,
                result,
            )

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
            for step, result in zip(
                executed_steps,
                results,
            )
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
            f"- {error['step']} " f"({error['unit']}): " f"{error['error']}" for error in errors
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

        execution = context.get(
            "execution",
            {},
        )

        completed_steps = execution.get(
            "steps",
            {},
        )

        for dependency_id in step.depends_on:
            dependency = completed_steps.get(dependency_id)

            if dependency is None:
                return "Dependencia no ejecutada: " f"{dependency_id}"

            if dependency.get("status") != "completed":
                return "Dependencia fallida: " f"{dependency_id}"

        return None

    # =========================================================
    # Evaluation
    # =========================================================

    def _evaluate(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> ExecutionResult:

        if not plan.metadata.get(
            "requires_self_critic",
            False,
        ):
            return result

        if result.is_failure:
            return result

        evaluation = self.critic.evaluate(
            plan,
            result,
        )

        result.metadata["evaluation"] = evaluation

        try:
            self.engram.save(
                (f"SelfCritic: {plan.id} - " f"score={evaluation.get('score')}"),
                tags=[
                    "self_critic",
                    f"plan_{plan.id}",
                    (f"score_" f"{evaluation.get('score', 0)}"),
                ],
            )
        except Exception:
            pass

        if evaluation.get(
            "pass",
            True,
        ):
            return result

        corrections = evaluation.get(
            "corrections",
            [],
        )

        self._retry_context[plan.id] = {
            "corrections": corrections,
            "issues": evaluation.get(
                "issues",
                [],
            ),
        }

        return ExecutionResult.retry(
            plan_id=plan.id,
            error=evaluation.get(
                "reason",
                "Evaluación fallida",
            ),
            retries=result.retries + 1,
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
            logger.warning(
                "Learning post-ejecución falló: %s",
                exc,
            )

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

                missing = [
                    dependency for dependency in step.depends_on if dependency not in available_ids
                ]

                if missing:
                    raise ValueError(f"Dependencias inexistentes: {missing}")

                if all(dependency in resolved for dependency in step.depends_on):
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

    def _update_metrics(
        self,
        result: ExecutionResult,
    ) -> None:

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

    def _fail(
        self,
        plan: ExecutionPlan,
        error: str,
    ) -> ExecutionResult:

        logger.error(
            "Plan %s falló: %s",
            plan.id,
            error,
        )

        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )
