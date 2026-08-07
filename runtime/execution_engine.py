from __future__ import annotations

import logging
import time
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.context.manager import ContextManager
from core.intent import IntentAnalyzer
from core.planning import PlanBuilder

from runtime.dispatcher import UnitDispatcher
from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Único dueño del lifecycle de ejecución.

    Coordina las etapas, no las implementa.

    Flujo:
        User input → IntentAnalyzer → PlanBuilder → ExecutionPlan
        → validate → context → execute → evaluate → finalize → ExecutionResult

    Etapas:
        1. Validación del plan
        2. Construcción de contexto
        3. Ejecución (single o multi-step)
        4. Evaluación (SelfCritic, opcional)
        5. Reintentos (si falla y hay retries)
        6. Aprendizaje post-ejecución (desacoplado)
        7. Finalización y resultado
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_registry: AgentRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        context_manager: ContextManager | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
    ):
        self.agent_registry = agent_registry or AgentRegistry()
        self.skill_registry = skill_registry or SkillRegistry()
        self.context_manager = context_manager or ContextManager()
        self.intent_analyzer = intent_analyzer or IntentAnalyzer()
        self.plan_builder = plan_builder or PlanBuilder()

        self.dispatcher = UnitDispatcher(
            agent_registry=self.agent_registry,
            skill_registry=self.skill_registry,
        )

        self.metrics = {
            "executions": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "cancelled": 0,
            "retries": 0,
        }

        # Cargar SelfCritic (helper, no agente)
        try:
            from core.self_critic import SelfCritic

            self.critic = SelfCritic()
        except ImportError:
            logger.warning("SelfCritic no disponible")
            self.critic = None

        # Cargar ContinuousLearner (opcional, post-ejecución)
        try:
            from core.learner import ContinuousLearner

            self.learner = ContinuousLearner()
        except ImportError:
            logger.warning("ContinuousLearner no disponible")
            self.learner = None

    # ==========================================================
    # Public API
    # ==========================================================

    def execute_from_input(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        logger.info("Engine: procesando entrada: %s", user_input[:100])

        intent = self.intent_analyzer.analyze(user_input)
        plan = self.plan_builder.build(intent=intent, original_task=user_input)

        if metadata:
            plan.metadata.update(metadata)

        return self.execute(plan)

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        started = time.monotonic()
        self.metrics["executions"] += 1

        try:
            # 1. Validación
            errors = plan.validate()
            if errors:
                return self._fail(plan, "; ".join(errors))

            plan.mark_validated()
            plan.mark_running()

            # 2. Contexto
            context = self.context_manager.build(plan) or {}
            plan.loaded_context = context

            # 3. Ejecución
            result = self._execute_with_retries(plan, context)

            # 4. Duración y metadata
            duration = round(time.monotonic() - started, 3)
            result.metadata.update(
                {
                    "engine": self.name,
                    "duration": duration,
                    "plan_id": plan.id,
                }
            )

            # 5. Aplicar estado al plan
            self._apply_plan_state(plan, result)
            self._update_metrics(result)

            # 6. Aprendizaje post-ejecución (desacoplado, no bloquea)
            self._learn(plan, result)

            return result

        except Exception as exc:
            logger.exception("Engine error")
            try:
                plan.mark_failed()
            except Exception:
                pass
            return self._fail(plan, str(exc))

    # ==========================================================
    # Ejecución con reintentos
    # ==========================================================

    def _execute_with_retries(self, plan: ExecutionPlan, context: dict) -> ExecutionResult:
        """
        Ejecuta el plan con reintentos controlados.
        """
        max_retries = plan.metadata.get("max_retries", plan.max_retries)
        retries = 0
        last_result = None

        while retries <= max_retries:
            # Ejecutar
            if plan.is_multi_step():
                result = self._execute_steps(plan, context)
            else:
                result = self._execute_single(plan, context)

            # Evaluar (SelfCritic)
            result = self._evaluate(plan, result)

            # Si pasa, devolver
            if result.is_success or result.is_partial:
                return result

            # Si falla y hay reintentos disponibles
            if result.is_failure and retries < max_retries:
                retries += 1
                self.metrics["retries"] += 1
                logger.info("Reintentando plan %s (intento %d/%d)", plan.id, retries, max_retries)
                result.metadata["retry_count"] = retries
                # Pequeña pausa antes de reintentar
                time.sleep(0.5)
                last_result = result
                continue

            # Si no hay más reintentos, devolver fallo
            return result

        # Si se agotaron los reintentos
        return last_result or ExecutionResult.fail(
            plan_id=plan.id,
            error="Se agotaron los reintentos",
            executor=self.name,
        )

    # ==========================================================
    # Etapas de ejecución
    # ==========================================================

    def _execute_single(self, plan: ExecutionPlan, context: dict) -> ExecutionResult:
        if not plan.execution_unit_type or not plan.execution_unit:
            return self._fail(plan, "Plan sin unidad de ejecución.")

        step = ExecutionStep(
            description=plan.objective or plan.original_task,
            unit_type=plan.execution_unit_type,
            unit_name=plan.execution_unit,
            params=plan.params,
        )
        return self.dispatcher.dispatch(plan, step, context)

    def _execute_steps(self, plan: ExecutionPlan, context: dict) -> ExecutionResult:
        if not plan.steps:
            return self._fail(plan, "Plan multi_step sin pasos.")

        ordered = self._resolve_order(plan.steps)
        results: list[ExecutionResult] = []
        failed_steps: list[str] = []

        for step in ordered:
            result = self.dispatcher.dispatch(plan, step, context)
            results.append(result)

            if result.is_failure:
                failed_steps.append(step.id)
                if plan.stop_on_error:
                    break

        if not failed_steps:
            return ExecutionResult.success(
                plan_id=plan.id,
                result=[r.result for r in results],
                executor=self.name,
            )
        elif not results:
            return self._fail(plan, "Todos los steps fallaron.")
        else:
            return ExecutionResult.partial(
                plan_id=plan.id,
                result=[r.result for r in results],
                error=f"Fallaron {len(failed_steps)} pasos",
                executor=self.name,
            )

    # ==========================================================
    # Evaluación (SelfCritic)
    # ==========================================================

    def _evaluate(self, plan: ExecutionPlan, result: ExecutionResult) -> ExecutionResult:
        """
        Etapa de evaluación post-ejecución.
        """
        # Si no se requiere crítica, pasar
        if not plan.metadata.get("requires_self_critic", False):
            return result

        # Si ya es fallo, no criticar
        if result.is_failure:
            return result

        if self.critic is None:
            return result

        try:
            evaluation = self.critic.evaluate(plan, result)
            if evaluation.get("pass", True):
                return result
            else:
                # Si la crítica falla, marcar como retry
                return ExecutionResult.retry(
                    plan_id=plan.id,
                    error=evaluation.get("reason", "Evaluación fallida"),
                    retries=result.retries + 1,
                    executor="self_critic",
                )
        except Exception as exc:
            logger.warning("SelfCritic falló: %s", exc)
            return result

    # ==========================================================
    # Aprendizaje post-ejecución
    # ==========================================================

    def _learn(self, plan: ExecutionPlan, result: ExecutionResult) -> None:
        """
        Aprendizaje continuo post-ejecución (no bloquea).
        """
        if self.learner is None:
            return

        if not result.is_success and not result.is_partial:
            return

        try:
            # Extraer aprendizaje de la interacción
            self.learner.extract_and_learn(
                user_query=plan.original_task,
                assistant_response=str(result.result or result.error or ""),
            )
        except Exception as exc:
            logger.debug("Aprendizaje continuo falló: %s", exc)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _resolve_order(self, steps: list[ExecutionStep]) -> list[ExecutionStep]:
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

    def _apply_plan_state(self, plan: ExecutionPlan, result: ExecutionResult) -> None:
        if result.is_success:
            plan.mark_completed()
        elif result.is_partial:
            plan.mark_partial()
        elif result.is_failure:
            plan.mark_failed()
        elif result.is_cancelled:
            plan.mark_cancelled()

    def _update_metrics(self, result: ExecutionResult) -> None:
        if result.is_success:
            self.metrics["success"] += 1
        elif result.is_partial:
            self.metrics["partial"] += 1
        elif result.is_failure:
            self.metrics["failed"] += 1
        elif result.is_cancelled:
            self.metrics["cancelled"] += 1
        elif result.is_retry:
            self.metrics["retries"] += 1

    def _fail(self, plan: ExecutionPlan, error: str) -> ExecutionResult:
        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.copy()
