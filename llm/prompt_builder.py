from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PromptType(str, Enum):
    """
    Tipo semántico del prompt construido.

    PromptBuilder construye el prompt, pero no selecciona
    proveedores ni ejecuta operaciones.
    """

    DEFAULT = "default"
    CRITIQUE = "critique"


class PromptBuilder:
    """
    Construye prompts deterministas para proveedores LLM.

    Responsabilidades:
        - Convertir ExecutionPlan + contexto en un prompt.
        - Normalizar, priorizar y limitar el contexto.
        - Separar instrucciones, tarea, plan y evidencia.
        - Preservar hechos vs inferencias.
        - Modo lean para generación de código / landings.

    No:
        - Selecciona proveedores.
        - Ejecuta herramientas.
        - Decide planificación.
        - Ejecuta Agents o Skills.
        - Modifica el ExecutionPlan.
    """

    MAX_CONTEXT_CHARS = 30_000

    # Presupuesto por clave (chars serializados) en modo normal.
    # En lean se aplican límites más estrictos.
    KEY_BUDGETS: dict[str, int] = {
        "architecture": 12_000,
        "project_analysis": 2_000,
        "project_summary": 1_500,
        "standards": 6_000,
        "engram": 3_000,
        "obsidian": 3_000,
        "gentleman": 2_000,
        "swarmforge": 2_000,
        "execution": 2_500,
        "dependency_text": 4_000,
        "code_artifacts": 2_000,
        "coding_task": 4_000,
        "requested_output": 2_000,
        "requested_paths": 500,
        "locale": 800,
        "locale_summary": 1_200,
    }

    LEAN_KEY_BUDGETS: dict[str, int] = {
        "architecture": 4_000,
        "project_analysis": 800,
        "project_summary": 800,
        "standards": 4_000,
        "engram": 1_500,
        "execution": 800,
        "dependency_text": 3_000,
        "coding_task": 4_000,
        "requested_output": 2_000,
        "requested_paths": 400,
        "locale_summary": 800,
    }

    # Claves que nunca deben entrar al prompt (ruido / tamaño).
    DROP_KEYS = frozenset(
        {
            "snapshot",
            "architecture_context",  # se normaliza a "architecture"
            "project",  # provider crudo; usar project_summary / architecture
            "loaded_context",
            "memory",
            "conversation_history",  # multi_turn lo maneja aparte si aplica
        }
    )

    SYSTEM_INSTRUCTIONS = """
Eres un ingeniero de software senior y arquitecto de sistemas.

Tu respuesta debe basarse únicamente en la evidencia proporcionada
por la tarea, el ExecutionPlan y el contexto disponible.

Reglas obligatorias:

1. No inventes componentes, archivos, tecnologías, servicios ni capacidades.
2. No afirmes como hecho aquello que solo puede inferirse.
3. Diferencia explícitamente entre:
   - hechos observados;
   - inferencias razonables;
   - información desconocida.
4. No confundas una estructura de carpetas con un límite arquitectónico.
5. No describas un sistema como microservicios sin evidencia explícita.
6. No inventes infraestructura, bases de datos, colas, APIs o comunicaciones
   que no estén presentes en la evidencia.
7. Si la información disponible es insuficiente, indícalo claramente.
8. Prioriza la implementación y evidencia real sobre descripciones genéricas.
9. Respeta las restricciones y requisitos incluidos en el contexto
   (standards, estilo de código, design system, contratos de pagos).
10. No inventes stack (framework, ORM, librería UI) no pedido en la tarea.
11. Operaciones de cobro/facturación: respeta contratos e idempotencia si aplican.
12. Responde en español salvo que la tarea solicite explícitamente otro idioma.
""".strip()

    CRITIQUE_INSTRUCTIONS = """
## Modo de evaluación

Debes evaluar el resultado de la ejecución respecto de la tarea,
el ExecutionPlan y la evidencia disponible.

Determina:

1. si la tarea fue completada correctamente;
2. qué problemas concretos existen;
3. qué correcciones serían necesarias;
4. una puntuación de 0 a 10;
5. una justificación breve.

Debes devolver EXCLUSIVAMENTE un objeto JSON válido.

El JSON debe tener exactamente esta estructura:

{
  "pass": true,
  "score": 10,
  "issues": [],
  "corrections": [],
  "reason": "Explicación breve."
}

Reglas:

- "pass" debe ser booleano.
- "score" debe ser un entero entre 0 y 10.
- "issues" debe ser una lista de strings.
- "corrections" debe ser una lista de strings.
- "reason" debe ser un string.
- No incluyas Markdown.
- No incluyas bloques ```json.
- No incluyas texto antes ni después del JSON.
- No inventes errores que no puedan justificarse con la evidencia.
- Si la evidencia no permite determinar algo, indícalo en "reason".
""".strip()

    # Orden de inclusión (prioridad alta → baja).
    CONTEXT_PRIORITY = (
        "agent_role",
        "coding_task",
        "requested_output",
        "requested_paths",
        "analysis_requirements",
        "standards",
        "locale_summary",
        "locale",
        "project_summary",
        "architecture",
        "project_analysis",
        "dependency_text",
        "code_artifacts",
        "gentleman",
        "swarmforge",
        "engram",
        "obsidian",
        "retry_issues",
        "retry_corrections",
        "execution",
        "additional_instructions",
        "lean_prompt",
    )

    SPECIALIZED_CONTEXT_KEYS = frozenset(
        {
            "agent_role",
            "analysis_requirements",
            "requested_output",
            "requested_paths",
            "coding_task",
            "retry_issues",
            "retry_corrections",
            "execution",
            "lean_prompt",
            "additional_instructions",
        }
    )

    def __init__(
        self,
        max_context_chars: int | None = None,
    ) -> None:
        self.max_context_chars = (
            max_context_chars if max_context_chars is not None else self.MAX_CONTEXT_CHARS
        )
        if self.max_context_chars <= 0:
            raise ValueError("max_context_chars debe ser mayor que cero.")

    # ==========================================================
    # Public API
    # ==========================================================

    def build(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
        prompt_type: PromptType = PromptType.DEFAULT,
    ) -> str:
        if plan is None:
            raise ValueError("plan no puede ser None.")

        if not isinstance(prompt_type, PromptType):
            try:
                prompt_type = PromptType(prompt_type)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"prompt_type inválido: {prompt_type!r}") from exc

        raw_context = dict(context or {})
        lean = self._is_lean(plan, raw_context)

        logger.info(
            "Construyendo prompt | plan=%s | type=%s | lean=%s | context=%s",
            plan.id,
            prompt_type.value,
            lean,
            list(raw_context.keys()),
        )

        prepared_context = self._prepare_context(raw_context, lean=lean)

        sizes = {
            k: len(self._serialize(v)) if not isinstance(v, str) else len(v)
            for k, v in prepared_context.items()
        }
        logger.info(
            "PromptBuilder | prepared_context_chars=%s | total=%s",
            sizes,
            sum(sizes.values()),
        )

        prompt = self._compose(
            plan=plan,
            context=prepared_context,
            prompt_type=prompt_type,
            lean=lean,
        )

        if len(prompt) > self.max_context_chars:
            logger.warning(
                "Prompt excede límite | chars=%s | max=%s",
                len(prompt),
                self.max_context_chars,
            )
            prompt = self._truncate_prompt(prompt)

        logger.info(
            "Prompt construido | plan=%s | type=%s | chars=%s",
            plan.id,
            prompt_type.value,
            len(prompt),
        )
        return prompt

    # ==========================================================
    # Lean detection
    # ==========================================================

    @staticmethod
    def _is_lean(plan: ExecutionPlan, context: dict[str, Any]) -> bool:
        if context.get("lean_prompt") in (True, "true", "1", 1):
            return True
        meta = getattr(plan, "metadata", None) or {}
        if meta.get("lean_prompt") is True:
            return True
        # Generación de código / landings / enrich: preferir lean
        intent = (getattr(plan, "intent", None) or "").lower()
        category = (getattr(plan, "intent_category", None) or "").lower()
        if intent in {
            "file_creation",
            "code_generation",
            "ui_scaffold",
            "module_scaffold",
        }:
            return True
        if category in {"code", "file"}:
            return True
        if context.get("coding_task"):
            return True
        return False

    # ==========================================================
    # Context preparation
    # ==========================================================

    def _prepare_context(
        self,
        context: dict[str, Any],
        *,
        lean: bool,
    ) -> dict[str, Any]:
        prepared: dict[str, Any] = {}
        processed: set[str] = set()
        budgets = self.LEAN_KEY_BUDGETS if lean else self.KEY_BUDGETS

        # Normalizar aliases → claves canónicas
        context = self._normalize_aliases(dict(context))

        for key in self.CONTEXT_PRIORITY:
            if key not in context or key in self.DROP_KEYS:
                continue
            value = context[key]
            if value is None:
                continue
            value = self._sanitize_context_value(key, value, lean=lean)
            value = self._apply_budget(key, value, budgets)
            if value is None or value == "" or value == {} or value == []:
                continue
            prepared[key] = value
            processed.add(key)

        for key, value in context.items():
            if key in processed or key in self.DROP_KEYS:
                continue
            if value is None:
                continue
            value = self._sanitize_context_value(key, value, lean=lean)
            value = self._apply_budget(key, value, budgets)
            if value is None or value == "" or value == {} or value == []:
                continue
            prepared[key] = value

        return prepared

    def _normalize_aliases(self, context: dict[str, Any]) -> dict[str, Any]:
        # architecture_context → architecture (sin contents)
        if "architecture" not in context and "architecture_context" in context:
            context["architecture"] = context.get("architecture_context")

        # project_analysis dict → summary preferido
        pa = context.get("project_analysis")
        if isinstance(pa, dict):
            if not context.get("project_summary"):
                summary = pa.get("summary") or pa.get("project_summary")
                if summary:
                    context["project_summary"] = summary
            # No arrastrar snapshot embebido
            if "snapshot" in pa:
                pa = {k: v for k, v in pa.items() if k in {"summary", "project_summary", "type"}}
                context["project_analysis"] = pa

        # locale_summary desde dict locale_info
        if not context.get("locale_summary") and isinstance(context.get("locale"), dict):
            loc = context["locale"]
            context["locale_summary"] = loc.get("locale_summary") or loc.get("summary")
            if not context.get("locale") or isinstance(context.get("locale"), dict):
                code = loc.get("locale_code") or loc.get("code")
                if code:
                    context["locale"] = code

        return context

    def _sanitize_context_value(
        self,
        key: str,
        value: Any,
        *,
        lean: bool,
    ) -> Any:
        if key == "architecture":
            return self._sanitize_architecture(value, lean=lean)
        if key == "execution":
            return self._sanitize_execution(value, lean=lean)
        if key == "project_analysis":
            return self._sanitize_project_analysis(value)
        if key in {"retry_issues", "retry_corrections"}:
            return self._sanitize_list(value)
        if key == "standards" and isinstance(value, (dict, list)):
            return value
        if key == "lean_prompt":
            return bool(value)
        return value

    def _apply_budget(
        self,
        key: str,
        value: Any,
        budgets: dict[str, int],
    ) -> Any:
        budget = budgets.get(key)
        if budget is None:
            return value
        if isinstance(value, str):
            if len(value) <= budget:
                return value
            return value[: budget - 20] + "\n[...truncado]"
        serialized = self._serialize(value)
        if len(serialized) <= budget:
            return value
        # Truncar representación serializada y devolver string
        return serialized[: budget - 20] + "\n[...truncado]"

    # ==========================================================
    # Architecture sanitization (sin contents)
    # ==========================================================

    def _sanitize_architecture(
        self,
        architecture: Any,
        *,
        lean: bool,
    ) -> Any:
        if not isinstance(architecture, dict):
            return architecture

        result: dict[str, Any] = {}

        for key in (
            "project_name",
            "root_path",
            "summary",
            "project_summary",
            "languages",
            "extensions",
            "directory_count",
            "file_count",
            "layers",
            "modules",
        ):
            if key in architecture and architecture[key] is not None:
                result[key] = architecture[key]

        files = architecture.get("files")
        if isinstance(files, list):
            clean_files = []
            limit = 40 if lean else 80
            for file_data in files[:limit]:
                if not isinstance(file_data, dict):
                    if isinstance(file_data, str):
                        clean_files.append({"path": file_data})
                    continue
                clean_file = {
                    k: file_data.get(k)
                    for k in (
                        "path",
                        "filename",
                        "extension",
                        "language",
                        "lines",
                        "size",
                    )
                    if k in file_data and file_data.get(k) is not None
                }
                # Nunca contents
                clean_files.append(clean_file)
            result["files"] = clean_files

        dirs = architecture.get("directories")
        if isinstance(dirs, list):
            clean_dirs = []
            for d in dirs[:40]:
                if isinstance(d, dict):
                    clean_dirs.append(
                        {
                            k: d.get(k)
                            for k in ("path", "name", "files_count", "directories_count")
                            if k in d
                        }
                    )
                elif isinstance(d, str):
                    clean_dirs.append({"path": d})
            result["directories"] = clean_dirs

        result.pop("content", None)
        result.pop("contents", None)
        result.pop("snapshot", None)
        return result

    @staticmethod
    def _sanitize_project_analysis(value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            k: value.get(k)
            for k in ("type", "summary", "project_summary")
            if value.get(k) is not None
        }

    @staticmethod
    def _sanitize_execution(execution: Any, *, lean: bool) -> Any:
        if not isinstance(execution, dict):
            return execution

        if lean:
            allowed = {
                "task",
                "current_step",
                "result",
            }
        else:
            allowed = {
                "plan_id",
                "task",
                "current_step",
                "dependencies",
                "steps",
                "result",
            }

        out = {key: execution.get(key) for key in allowed if key in execution}

        # Evitar volcar dependencias enormes en lean
        if lean and "result" in out and isinstance(out["result"], (dict, list, str)):
            blob = (
                out["result"]
                if isinstance(out["result"], str)
                else json.dumps(out["result"], ensure_ascii=False, default=str)
            )
            if len(blob) > 1200:
                out["result"] = blob[:1180] + "...[truncado]"
        return out

    @staticmethod
    def _sanitize_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if not isinstance(value, (list, tuple, set)):
            return [str(value)]
        return [str(item) for item in value if item is not None]

    # ==========================================================
    # Serialization
    # ==========================================================

    @staticmethod
    def _serialize(value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except Exception:
            logger.exception("Error serializando contexto.")
            return str(value)

    # ==========================================================
    # Plan representation
    # ==========================================================

    def _build_plan_section(
        self,
        plan: ExecutionPlan,
        *,
        lean: bool,
    ) -> str:
        if lean:
            plan_data: dict[str, Any] = {
                "plan_id": plan.id,
                "intent": plan.intent,
                "intent_category": plan.intent_category,
                "objective": plan.objective,
            }
            # Solo metadata útil
            meta = getattr(plan, "metadata", None) or {}
            slim_meta = {
                k: meta[k] for k in ("locale", "workflow", "enrich", "lean_prompt") if k in meta
            }
            if slim_meta:
                plan_data["metadata"] = slim_meta
            return self._serialize(plan_data)

        plan_data = {
            "plan_id": plan.id,
            "original_task": plan.original_task,
            "intent": plan.intent,
            "intent_category": plan.intent_category,
            "objective": plan.objective,
            "execution_unit_type": plan.execution_unit_type,
            "execution_unit": plan.execution_unit,
            "execution_policy": plan.execution_policy,
            "metadata": {
                k: v
                for k, v in (plan.metadata or {}).items()
                if k
                not in {
                    "loaded_context",
                    "execution_context",
                }
            },
        }
        if plan.steps:
            plan_data["steps"] = [
                {
                    "id": step.id,
                    "description": step.description,
                    "unit_type": step.unit_type,
                    "unit_name": step.unit_name,
                    "depends_on": list(step.depends_on),
                    "params": {
                        k: v
                        for k, v in dict(step.params or {}).items()
                        if k not in {"content"}  # no volcar content enorme
                    },
                }
                for step in plan.steps
            ]
        return self._serialize(plan_data)

    # ==========================================================
    # Prompt composition
    # ==========================================================

    def _compose(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        prompt_type: PromptType,
        *,
        lean: bool,
    ) -> str:
        sections: list[str] = [self.SYSTEM_INSTRUCTIONS]

        if prompt_type is PromptType.CRITIQUE:
            sections.append(self.CRITIQUE_INSTRUCTIONS)

        agent_role = context.get("agent_role")
        if agent_role:
            sections.append(self._section("Rol de ejecución", str(agent_role)))

        # Tarea: preferir coding_task si existe (enrich / coder)
        coding_task = context.get("coding_task")
        if coding_task:
            sections.append(self._section("Tarea de generación", str(coding_task)))
        else:
            sections.append(self._section("Tarea del usuario", plan.original_task or ""))

        sections.append(
            self._section(
                "ExecutionPlan",
                self._build_plan_section(plan, lean=lean),
            )
        )

        analysis_requirements = context.get("analysis_requirements")
        if analysis_requirements:
            sections.append(
                self._section(
                    "Requisitos de análisis",
                    self._serialize(analysis_requirements),
                )
            )

        requested_output = context.get("requested_output")
        if requested_output:
            sections.append(
                self._section(
                    "Formato de salida solicitado",
                    self._serialize(requested_output),
                )
            )

        requested_paths = context.get("requested_paths")
        if requested_paths:
            sections.append(
                self._section(
                    "Paths solicitados",
                    self._serialize(requested_paths),
                )
            )

        # Standards explícitos (consistencia full-stack)
        standards = context.get("standards")
        if standards:
            sections.append(
                self._section(
                    "Standards del proyecto (obligatorio respetar)",
                    self._serialize(standards),
                )
            )

        locale_summary = context.get("locale_summary") or context.get("locale")
        if locale_summary:
            sections.append(
                self._section(
                    "Locale / región",
                    self._serialize(locale_summary),
                )
            )

        project_summary = context.get("project_summary")
        if project_summary:
            sections.append(self._section("Resumen del proyecto", str(project_summary)))

        architecture = context.get("architecture")
        if architecture:
            sections.append(
                self._section(
                    "Arquitectura (estructura, sin contenidos de archivo)",
                    self._serialize(architecture),
                )
            )

        dependency_text = context.get("dependency_text")
        if dependency_text:
            sections.append(
                self._section(
                    "Salida de dependencia previa",
                    str(dependency_text),
                )
            )

        # Resto de evidencia (sin specialized)
        skip = set(self.SPECIALIZED_CONTEXT_KEYS) | {
            "standards",
            "locale",
            "locale_summary",
            "project_summary",
            "architecture",
            "dependency_text",
            "coding_task",
            "project_analysis",
        }
        general = {key: value for key, value in context.items() if key not in skip}
        if general:
            sections.append(
                self._section(
                    "Contexto y evidencia disponible",
                    self._serialize(general),
                )
            )

        retry_issues = context.get("retry_issues")
        retry_corrections = context.get("retry_corrections")
        if retry_issues or retry_corrections:
            sections.append(
                self._section(
                    "Correcciones de una ejecución anterior",
                    self._serialize(
                        {
                            "issues": retry_issues or [],
                            "corrections": retry_corrections or [],
                        }
                    ),
                )
            )

        execution = context.get("execution")
        if execution:
            sections.append(
                self._section(
                    "Evidencia de ejecución",
                    self._serialize(execution),
                )
            )

        additional = context.get("additional_instructions")
        if additional:
            sections.append(self._section("Instrucciones adicionales", str(additional)))

        if prompt_type is PromptType.CRITIQUE:
            sections.append(
                self._section(
                    "Instrucciones finales",
                    """
Evalúa exclusivamente el resultado disponible.

No ejecutes nuevamente la tarea.
No propongas cambios basados en información inexistente.
No confundas una limitación de evidencia con un error de ejecución.

Devuelve únicamente el JSON definido en "Modo de evaluación".
""".strip(),
                )
            )
        else:
            final = """
Realiza la tarea utilizando únicamente la información disponible.

Cuando debas analizar una implementación:
1. identifica primero los hechos observables;
2. separa las inferencias de los hechos;
3. indica explícitamente qué información no puede determinarse;
4. evita completar huecos con suposiciones;
5. respeta las restricciones del ExecutionPlan y los Standards;
6. si existe información de retry, corrige específicamente los problemas
   señalados sin introducir cambios no justificados.

Cuando generes código o HTML:
1. respeta formato de salida (code_artifact / paths) si se indicó;
2. no inventes stack ni design system nuevo;
3. no copies marcas ni claims de sitios de referencia;
4. operaciones de pago: contratos + idempotency_key si aplica.

La respuesta debe ser concreta, técnica y específica para el proyecto.
""".strip()
            sections.append(self._section("Instrucciones finales", final))

        return "\n\n".join(section.strip() for section in sections if section and section.strip())

    # ==========================================================
    # Section helper
    # ==========================================================

    @staticmethod
    def _section(title: str, content: str) -> str:
        return f"""
## {title}

{content}
""".strip()

    # ==========================================================
    # Truncation
    # ==========================================================

    def _truncate_prompt(self, prompt: str) -> str:
        limit = self.max_context_chars
        if len(prompt) <= limit:
            return prompt

        notice = (
            "\n\n[SYSTEM NOTICE]\n"
            "El contexto fue reducido por límite de tamaño. "
            "No inferir información ausente."
        )

        # Preferir recortar evidencia general y architecture
        for marker in (
            "## Contexto y evidencia disponible",
            "## Arquitectura (estructura, sin contenidos de archivo)",
            "## Evidencia de ejecución",
        ):
            context_index = prompt.find(marker)
            if context_index == -1:
                continue

            before = prompt[:context_index]
            final_marker = "\n## Instrucciones finales"
            final_index = prompt.find(final_marker, context_index)
            after = prompt[final_index:] if final_index != -1 else ""

            available = limit - len(before) - len(after) - len(notice)
            if available <= 200:
                continue

            rest = prompt[context_index + len(marker) :]
            if final_index != -1:
                rest = prompt[context_index + len(marker) : final_index]

            if len(rest) > available:
                rest = rest[:available] + "\n[CONTEXTO REDUCIDO]"

            result = before + marker + "\n\n" + rest.strip() + after + notice
            if len(result) <= limit:
                return result
            return result[:limit]

        return prompt[: max(0, limit - len(notice))] + notice
