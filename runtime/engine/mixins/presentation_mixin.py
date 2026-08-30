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

class EnginePresentationMixin:
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

