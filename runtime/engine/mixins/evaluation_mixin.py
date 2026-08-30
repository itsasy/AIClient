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

class EngineEvaluationMixin:
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

