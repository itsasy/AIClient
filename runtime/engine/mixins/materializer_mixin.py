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

class EngineMaterializerMixin:
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

