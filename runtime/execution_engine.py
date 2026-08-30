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

from runtime.engine.mixins.lifecycle_mixin import EngineLifecycleMixin
from runtime.engine.mixins.context_mixin import EngineContextMixin
from runtime.engine.mixins.materializer_mixin import EngineMaterializerMixin
from runtime.engine.mixins.executor_mixin import EngineExecutorMixin
from runtime.engine.mixins.retry_mixin import EngineRetryMixin
from runtime.engine.mixins.presentation_mixin import EnginePresentationMixin
from runtime.engine.mixins.evaluation_mixin import EngineEvaluationMixin


class ExecutionEngine(
    EngineLifecycleMixin,
    EngineContextMixin,
    EngineMaterializerMixin,
    EngineExecutorMixin,
    EngineRetryMixin,
    EnginePresentationMixin,
    EngineEvaluationMixin,
):
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
                plan.mark_failed(str(exc))
            except Exception:
                logger.exception("No se pudo marcar plan como failed")

            result = self._fail(plan, str(exc))
            return self._finalize(
                plan=plan,
                result=result,
                started_monotonic=started_monotonic,
                started_at=started_at,
            )

