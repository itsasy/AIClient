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

class EngineContextMixin:
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

