from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

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
from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Único dueño del lifecycle de ejecución.

    El ExecutionEngine ejecuta planes utilizando los registries
    proporcionados por la composición de la aplicación.

    No:
        - Carga Agents.
        - Carga Skills.
        - Gestiona AgentManager.
        - Gestiona SkillManager.
        - Decide cómo se descubren o registran unidades.

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
        validate → context → execute → evaluate → retry → finalize → learning
    """

    name = "execution_engine"

    SUCCESS_STATUSES = frozenset(
        {
            "completed",
            "success",
            "ok",
        }
    )

    def __init__(
        self,
        agent_registry: AgentRegistry,
        skill_registry: SkillRegistry,
        context_manager: ContextManager | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
        command_router: Any | None = None,
    ) -> None:
        if agent_registry is None:
            raise ValueError(
                "ExecutionEngine requiere agent_registry.",
            )

        if skill_registry is None:
            raise ValueError(
                "ExecutionEngine requiere skill_registry.",
            )

        self.agent_registry = agent_registry
        self.skill_registry = skill_registry

        self.context_manager = context_manager if context_manager is not None else ContextManager()

        self.intent_analyzer = intent_analyzer if intent_analyzer is not None else IntentAnalyzer()

        self.plan_builder = plan_builder if plan_builder is not None else PlanBuilder()

        self.command_router = command_router

        self.dispatcher = UnitDispatcher(
            agent_registry=self.agent_registry,
            skill_registry=self.skill_registry,
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

        logger.info(
            "Engine procesando entrada=%s",
            user_input[:100],
        )

        # Slash commands (/spec, /plan, …) antes del IntentAnalyzer
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

        intent = self.intent_analyzer.analyze(
            user_input,
        )

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

            context = self.context_manager.build(plan) or {}

            plan.loaded_context = dict(context)

            plan.mark_running()

            result = self._execute_with_retries(
                plan,
                context,
            )

            result = self._finalize(
                plan,
                result,
                started,
            )

            self._learn(
                plan,
                result,
            )

            return result

        except Exception as exc:
            logger.exception(
                "Error fatal en ExecutionEngine",
            )

            try:
                plan.mark_failed()
            except Exception:
                logger.exception(
                    "No se pudo marcar plan como failed",
                )

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

        self._update_metrics(
            result,
        )

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
                retry_count=getattr(
                    result,
                    "retries",
                    0,
                )
                or 0,
                error=result.error,
                step_count=len(plan.steps),
                metadata=dict(
                    plan.metadata or {},
                ),
            )

            self.metrics_store.save(
                metric,
            )

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
        """
        Construye un contexto aislado para el step.

        No modifica directamente el contexto raíz salvo a través
        de record_step_result(), que es responsabilidad del
        ContextManager.
        """

        step_context = dict(context)

        dependencies = self.context_manager.get_dependency_results(
            context,
            step,
        )

        if dependencies:
            execution = dict(
                step_context.get(
                    "execution",
                    {},
                )
                or {}
            )

            execution["dependencies"] = dependencies
            step_context["execution"] = execution

        self._materialize_dependency_outputs(
            step=step,
            dependencies=dependencies,
            step_context=step_context,
        )

        execution = dict(
            step_context.get(
                "execution",
                {},
            )
            or {}
        )

        execution["current_step"] = {
            "id": step.id,
            "description": step.description,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "params": dict(
                step.params or {},
            ),
        }

        step_context["execution"] = execution

        retry_data = self._retry_context.get(
            plan.id,
        )

        if retry_data:
            step_context["retry_corrections"] = list(
                retry_data.get(
                    "corrections",
                    [],
                )
                or []
            )

            step_context["retry_issues"] = list(
                retry_data.get(
                    "issues",
                    [],
                )
                or []
            )

        return step_context

    def _materialize_dependency_outputs(
        self,
        step: ExecutionStep,
        dependencies: dict[str, Any],
        step_context: dict[str, Any],
    ) -> None:
        """
        Proyecta outputs tipados de dependencias a:

          - step.params  (Skills)
          - step_context (Agents)

        Contratos:

          - code_artifact → write_file (path, content)
          - texto plano   → write_file.content
          - architecture_evidence / project_analysis → architect
        """

        if not dependencies:
            return

        artifacts: list[dict[str, Any]] = []
        evidence_by_type: dict[str, Any] = {}
        plain_texts: list[str] = []

        for dep_id, dep_data in dependencies.items():
            if not isinstance(
                dep_data,
                dict,
            ):
                continue

            status = dep_data.get(
                "status",
            )

            if status is not None and status not in self.SUCCESS_STATUSES:
                continue

            raw = dep_data.get(
                "result",
            )

            if raw is None:
                continue

            payload = raw

            if isinstance(raw, dict) and "ok" in raw and "result" in raw:
                if raw.get("ok") is False:
                    continue

                payload = raw.get(
                    "result",
                )

            if isinstance(
                payload,
                str,
            ):
                if payload.strip():
                    plain_texts.append(
                        payload,
                    )

                continue

            if not isinstance(
                payload,
                dict,
            ):
                continue

            payload_type = payload.get(
                "type",
            )

            if payload_type == "code_artifact":
                artifacts.append(
                    payload,
                )

            elif payload_type in (
                "architecture_evidence",
                "quality_evidence",
                "security_evidence",
                "performance_evidence",
                "project_analysis",
            ):
                evidence_by_type[payload_type] = payload

            elif "architecture" in payload and payload_type is None:
                evidence_by_type.setdefault(
                    "architecture_evidence",
                    payload,
                )

            elif payload_type is None and (
                "structure" in payload or "files" in payload or "project" in payload
            ):
                evidence_by_type.setdefault(
                    "project_analysis",
                    payload,
                )

        # ----------------------------------------------------------
        # Skills: write_file
        # ----------------------------------------------------------

        if step.unit_type == "skill" and step.unit_name == "write_file":
            params = dict(
                step.params or {},
            )

            needs_path = not params.get(
                "path",
            )

            needs_content = params.get("content") is None

            if (needs_path or needs_content) and artifacts:
                file_index = 0

                try:
                    file_index = int(
                        params.get(
                            "file_index",
                            0,
                        )
                        or 0
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    file_index = 0

                files = (
                    artifacts[0].get(
                        "files",
                    )
                    or []
                )

                if 0 <= file_index < len(files):
                    chosen = files[file_index]

                    if needs_path and chosen.get("path"):
                        params["path"] = chosen["path"]

                    if needs_content and chosen.get("content") is not None:
                        params["content"] = chosen["content"]

                    step.params = params

                    current = dict(
                        step_context.get(
                            "execution",
                            {},
                        )
                        or {}
                    )

                    current_step = dict(
                        current.get(
                            "current_step",
                            {},
                        )
                        or {}
                    )

                    current_step["params"] = dict(params)

                    current["current_step"] = current_step

                    step_context["execution"] = current

                    logger.info(
                        "Materializado write_file | path=%s | content_len=%s",
                        params.get("path"),
                        len(
                            str(
                                params.get(
                                    "content",
                                    "",
                                )
                            )
                        ),
                    )

                    needs_path = not params.get(
                        "path",
                    )

                    needs_content = params.get("content") is None

            # Fallback: texto plano de task_agent / multi_turn
            if needs_content and plain_texts:
                params = dict(
                    step.params or {},
                )

                text = plain_texts[0]
                content = text
                path_from_json = None

                stripped = text.strip()

                if "code_artifact" in stripped and "{" in stripped:
                    candidate = stripped

                    if candidate.startswith("```"):
                        lines = candidate.split(
                            "\n",
                        )

                        if lines and lines[0].startswith("```"):
                            lines = lines[1:]

                        if lines and lines[-1].strip().startswith("```"):
                            lines = lines[:-1]

                        candidate = "\n".join(
                            lines,
                        ).strip()

                    try:
                        data = json.loads(
                            candidate,
                        )

                    except json.JSONDecodeError:
                        start = candidate.find(
                            "{",
                        )

                        end = candidate.rfind(
                            "}",
                        )

                        data = None

                        if start >= 0 and end > start:
                            try:
                                data = json.loads(
                                    candidate[start : end + 1],
                                )
                            except json.JSONDecodeError:
                                data = None

                    if isinstance(data, dict) and data.get("type") == "code_artifact":
                        files = (
                            data.get(
                                "files",
                            )
                            or []
                        )

                        file_index = 0

                        try:
                            file_index = int(
                                params.get(
                                    "file_index",
                                    0,
                                )
                                or 0
                            )
                        except (
                            TypeError,
                            ValueError,
                        ):
                            file_index = 0

                        if 0 <= file_index < len(files):
                            chosen = files[file_index]

                            if isinstance(
                                chosen,
                                dict,
                            ):
                                if chosen.get("content") is not None:
                                    content = chosen["content"]

                                if chosen.get("path"):
                                    path_from_json = chosen["path"]

                params["content"] = content

                if needs_path and not params.get("path"):
                    params["path"] = path_from_json or "output.md"

                step.params = params

                current = dict(
                    step_context.get(
                        "execution",
                        {},
                    )
                    or {}
                )

                current_step = dict(
                    current.get(
                        "current_step",
                        {},
                    )
                    or {}
                )

                current_step["params"] = dict(params)

                current["current_step"] = current_step

                step_context["execution"] = current

                logger.info(
                    "Materializado write_file desde texto | path=%s | content_len=%s",
                    params.get("path"),
                    len(
                        str(
                            params.get(
                                "content",
                                "",
                            )
                        )
                    ),
                )

        # ----------------------------------------------------------
        # Agents: evidencia
        # ----------------------------------------------------------

        if step.unit_type == "agent":

            architecture_evidence = evidence_by_type.get(
                "architecture_evidence",
            )

            if isinstance(
                architecture_evidence,
                dict,
            ):
                step_context["architecture"] = architecture_evidence

                if not step_context.get("project_summary"):
                    step_context["project_summary"] = (
                        architecture_evidence.get("summary")
                        or architecture_evidence.get("project_summary")
                        or ""
                    )

            project_analysis = evidence_by_type.get(
                "project_analysis",
            )

            if isinstance(
                project_analysis,
                dict,
            ):
                architecture = project_analysis.get(
                    "architecture_context",
                )

                if isinstance(
                    architecture,
                    dict,
                ):
                    # architecture es la representación canónica.
                    # project_analysis queda como evidencia adicional;
                    # PromptBuilder elimina architecture_context para
                    # evitar serializar la misma evidencia dos veces.
                    step_context["architecture"] = architecture

                summary = (
                    project_analysis.get("summary") or project_analysis.get("project_summary") or ""
                )

                if summary and not step_context.get("project_summary"):
                    step_context["project_summary"] = summary

                step_context["project_analysis"] = project_analysis

            for key in (
                "quality_evidence",
                "security_evidence",
                "performance_evidence",
            ):
                evidence = evidence_by_type.get(key)

                if isinstance(
                    evidence,
                    dict,
                ):
                    step_context[key] = evidence

            if artifacts:
                step_context["code_artifacts"] = artifacts

            # Solo exponemos texto plano si no existe una evidencia
            # estructurada equivalente. Esto evita duplicar respuestas
            # completas dentro del prompt.
            if plain_texts and not (architecture_evidence or project_analysis or artifacts):
                step_context["dependency_text"] = plain_texts[0]

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
                    # No devolver status transitorio "retry" como resultado final.
                    if result.status == "retry" or getattr(result, "is_retry", False):
                        return ExecutionResult.fail(
                            plan_id=plan.id,
                            error=(
                                result.error
                                or "SelfCritic: reintentos agotados sin superar la evaluación"
                            ),
                            executor=result.executor or self.name,
                            metadata={
                                **dict(result.metadata or {}),
                                "retry_exhausted": True,
                                "retry_count": retries,
                            },
                        )
                    return result

                retries += 1
                self.metrics["retries"] += 1
                result.metadata["retry_count"] = retries

                retry_data = self._retry_context.get(plan.id) or {}
                logger.info(
                    "Retry plan=%s intento=%s/%s | corrections=%s | issues=%s",
                    plan.id,
                    retries,
                    max_retries,
                    len(retry_data.get("corrections") or []),
                    len(retry_data.get("issues") or []),
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
    # Single / multi
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
            params=dict(
                plan.params or {},
            ),
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
            step.mark_failed(
                str(exc),
            )

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
    # Scaffold aggregation
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

        locale = plan.metadata.get(
            "locale",
        )

        for item in results:
            if item.error:
                errors.append(
                    str(item.error),
                )

            raw = item.result

            if isinstance(raw, dict) and "ok" in raw and "result" in raw:
                if raw.get("ok") is False and raw.get("error"):
                    errors.append(
                        str(raw["error"]),
                    )

                raw = raw.get(
                    "result",
                )

            if not isinstance(
                raw,
                dict,
            ):
                continue

            mod = raw.get(
                "module",
            )

            if mod:
                modules.append(
                    str(mod),
                )

            for path in raw.get("created") or []:
                p = str(path)
                created.append(p)

                if "/adapters/" in p.replace(
                    "\\",
                    "/",
                ):
                    adapters.append(p)

        def uniq(
            seq: list[str],
        ) -> list[str]:
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
            "from_spec": plan.metadata.get(
                "from_spec",
            ),
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

        if plan.metadata.get(
            "aggregate_results",
        ):
            return True

        intent = (plan.intent or "").lower()

        if intent in {
            "module_scaffold",
            "ui_scaffold",
        }:
            return True

        names = [f"{step.unit_type}:{step.unit_name}" for step in plan.steps]

        scaffoldish = sum(
            1
            for name in names
            if name
            in {
                "skill:scaffold_module",
                "skill:scaffold_ui_shell",
                "skill:write_file",
            }
        )

        return scaffoldish >= 2

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

        ordered = self._resolve_order(
            plan.steps,
        )

        results: list[ExecutionResult] = []
        executed_steps: list[ExecutionStep] = []
        errors: list[dict[str, str]] = []

        for step in ordered:
            dependency_failure = self._dependency_failure(
                step,
                context,
            )

            if dependency_failure is not None:
                step.mark_skipped(
                    dependency_failure,
                )

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
                step.mark_failed(
                    str(exc),
                )

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
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": (result.error or "Error desconocido"),
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
            if self._should_aggregate_scaffold(
                plan,
                results,
            ):
                final_result = self._aggregate_scaffold_results(
                    plan,
                    results,
                )
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
                        isinstance(
                            final_result,
                            dict,
                        )
                        and final_result.get(
                            "type",
                        )
                        == "module_scaffold_batch"
                    ),
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
            dependency = completed_steps.get(
                dependency_id,
            )

            if dependency is None:
                return "Dependencia no ejecutada: " f"{dependency_id}"

            status = dependency.get(
                "status",
            )

            error = dependency.get(
                "error",
            )

            if status in self.SUCCESS_STATUSES:
                continue

            if error is None and dependency.get("result") is not None:
                continue

            return "Dependencia fallida: " f"{dependency_id} " f"(status={status})"

        return None

    # =========================================================
    # Evaluation / learning
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
                    ("score_" f"{evaluation.get('score', 0)}"),
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
            retries=getattr(
                result,
                "retries",
                0,
            )
            + 1,
            executor="self_critic",
            metadata={
                "evaluation": evaluation,
                "corrections": corrections,
            },
        )

    def _learn(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        if not (result.is_success or result.is_partial):
            return

        try:
            proposed = self.learner.extract_and_learn(
                user_query=plan.original_task,
                assistant_response=str(
                    result.result or result.error or "",
                ),
            )
            if proposed:
                logger.info(
                    "Learning candidate creado | plan=%s | task=%s",
                    plan.id,
                    (plan.original_task or "")[:80],
                )
        except Exception as exc:
            logger.warning(
                "Learning post-ejecución falló: %s",
                exc,
            )

    # =========================================================
    # Ordering / state / metrics
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
                    raise ValueError(
                        "Dependencias inexistentes: " f"{missing}",
                    )

                if all(dependency in resolved for dependency in step.depends_on):
                    ordered.append(step)
                    resolved.add(step.id)
                    pending.remove(step)
                    progress = True

            if not progress:
                raise RuntimeError(
                    "Dependencias circulares en el plan.",
                )

        return ordered

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
