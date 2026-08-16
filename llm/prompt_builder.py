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
        - Normalizar y limitar el contexto.
        - Separar instrucciones, tarea, plan y evidencia.
        - Preservar la distinción entre hechos e inferencias.
        - Construir variantes semánticas del prompt.

    No:
        - Selecciona proveedores.
        - Ejecuta herramientas.
        - Decide planificación.
        - Ejecuta Agents o Skills.
        - Modifica el ExecutionPlan.
    """

    MAX_CONTEXT_CHARS = 30_000

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
9. Respeta las restricciones y requisitos incluidos en el contexto.
10. Responde en español salvo que la tarea solicite explícitamente otro idioma.
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
- No incluy Markdown.
- No incluy bloques ```json.
- No incluy texto antes ni después del JSON.
- No inventes errores que no puedan justificarse con la evidencia.
- Si la evidencia no permite determinar algo, indícalo en "reason".
""".strip()

    CONTEXT_PRIORITY = (
        "agent_role",
        "analysis_requirements",
        "requested_output",
        "project_summary",
        "architecture",
        "project_analysis",
        "standards",
        "gentleman",
        "swarmforge",
        "engram",
        "retry_issues",
        "retry_corrections",
        "execution",
        "additional_instructions",
    )

    SPECIALIZED_CONTEXT_KEYS = {
        "agent_role",
        "analysis_requirements",
        "requested_output",
        "retry_issues",
        "retry_corrections",
        "execution",
    }

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
        """
        Construye el prompt final para el proveedor LLM.

        prompt_type determina la intención semántica del prompt,
        pero no modifica el ExecutionPlan ni selecciona proveedores.
        """

        if plan is None:
            raise ValueError("plan no puede ser None.")

        if not isinstance(prompt_type, PromptType):
            try:
                prompt_type = PromptType(prompt_type)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"prompt_type inválido: {prompt_type!r}") from exc

        raw_context = dict(context or {})

        logger.info(
            "Construyendo prompt | plan=%s | type=%s | context=%s",
            plan.id,
            prompt_type.value,
            list(raw_context.keys()),
        )

        prepared_context = self._prepare_context(
            raw_context,
        )

        prompt = self._compose(
            plan=plan,
            context=prepared_context,
            prompt_type=prompt_type,
        )

        if len(prompt) > self.max_context_chars:
            logger.warning(
                "Prompt excede límite | chars=%s | max=%s",
                len(prompt),
                self.max_context_chars,
            )

            prompt = self._truncate_prompt(
                prompt,
            )

        logger.info(
            "Prompt construido | plan=%s | type=%s | chars=%s",
            plan.id,
            prompt_type.value,
            len(prompt),
        )

        return prompt

    # ==========================================================
    # Context preparation
    # ==========================================================

    def _prepare_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normaliza el contexto respetando la prioridad declarada.

        Las claves conocidas aparecen primero. Las claves adicionales
        también se conservan para evitar pérdida silenciosa de evidencia.
        """

        prepared: dict[str, Any] = {}
        processed_keys: set[str] = set()

        # ------------------------------------------------------
        # Contexto prioritario
        # ------------------------------------------------------

        for key in self.CONTEXT_PRIORITY:
            if key not in context:
                continue

            value = context[key]

            if value is None:
                continue

            value = self._sanitize_context_value(
                key,
                value,
            )

            prepared[key] = value
            processed_keys.add(key)

        # ------------------------------------------------------
        # Contexto adicional
        # ------------------------------------------------------

        for key, value in context.items():
            if key in processed_keys:
                continue

            if value is None:
                continue

            prepared[key] = self._sanitize_context_value(
                key,
                value,
            )

        return prepared

    def _sanitize_context_value(
        self,
        key: str,
        value: Any,
    ) -> Any:
        if key == "architecture":
            return self._sanitize_architecture(value)

        if key == "execution":
            return self._sanitize_execution(value)

        if key in {
            "retry_issues",
            "retry_corrections",
        }:
            return self._sanitize_list(value)

        return value

    # ==========================================================
    # Architecture sanitization
    # ==========================================================

    def _sanitize_architecture(
        self,
        architecture: Any,
    ) -> Any:
        if not isinstance(
            architecture,
            dict,
        ):
            return architecture

        result = dict(architecture)

        files = result.get("files")

        if isinstance(
            files,
            list,
        ):
            clean_files = []

            for file_data in files:
                if not isinstance(
                    file_data,
                    dict,
                ):
                    continue

                clean_file = {
                    key: file_data.get(key)
                    for key in (
                        "path",
                        "filename",
                        "extension",
                        "language",
                        "lines",
                        "size",
                        "content",
                    )
                    if key in file_data
                }

                clean_files.append(clean_file)

            result["files"] = clean_files

        return result

    # ==========================================================
    # Execution sanitization
    # ==========================================================

    @staticmethod
    def _sanitize_execution(
        execution: Any,
    ) -> Any:
        """
        Expone la información necesaria para comprender
        la ejecución actual y evaluar su resultado.
        """

        if not isinstance(
            execution,
            dict,
        ):
            return execution

        allowed_keys = {
            "plan_id",
            "task",
            "current_step",
            "dependencies",
            "steps",
            "result",
        }

        return {key: execution.get(key) for key in allowed_keys if key in execution}

    # ==========================================================
    # Generic sanitization
    # ==========================================================

    @staticmethod
    def _sanitize_list(
        value: Any,
    ) -> list[str]:
        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            return [value]

        if not isinstance(
            value,
            (list, tuple, set),
        ):
            return [str(value)]

        return [str(item) for item in value if item is not None]

    # ==========================================================
    # Serialization
    # ==========================================================

    @staticmethod
    def _serialize(
        value: Any,
    ) -> str:
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
    ) -> str:
        plan_data = {
            "plan_id": plan.id,
            "original_task": plan.original_task,
            "intent": plan.intent,
            "intent_category": plan.intent_category,
            "objective": plan.objective,
            "execution_unit_type": plan.execution_unit_type,
            "execution_unit": plan.execution_unit,
            "execution_policy": plan.execution_policy,
            "metadata": plan.metadata,
        }

        if plan.steps:
            plan_data["steps"] = [
                {
                    "id": step.id,
                    "description": step.description,
                    "unit_type": step.unit_type,
                    "unit_name": step.unit_name,
                    "depends_on": list(step.depends_on),
                    "params": dict(step.params),
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
    ) -> str:

        sections: list[str] = [
            self.SYSTEM_INSTRUCTIONS,
        ]

        if prompt_type is PromptType.CRITIQUE:
            sections.append(self.CRITIQUE_INSTRUCTIONS)

        # ------------------------------------------------------
        # Agent role
        # ------------------------------------------------------

        agent_role = context.get("agent_role")

        if agent_role:
            sections.append(
                self._section(
                    "Rol de ejecución",
                    str(agent_role),
                )
            )

        # ------------------------------------------------------
        # Task
        # ------------------------------------------------------

        sections.append(
            self._section(
                "Tarea del usuario",
                plan.original_task,
            )
        )

        # ------------------------------------------------------
        # Plan
        # ------------------------------------------------------

        sections.append(
            self._section(
                "ExecutionPlan",
                self._build_plan_section(plan),
            )
        )

        # ------------------------------------------------------
        # Requirements
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # General evidence
        # ------------------------------------------------------

        general_context = {
            key: value for key, value in context.items() if key not in self.SPECIALIZED_CONTEXT_KEYS
        }

        if general_context:
            sections.append(
                self._section(
                    "Contexto y evidencia disponible",
                    self._serialize(general_context),
                )
            )

        # ------------------------------------------------------
        # Retry information
        # ------------------------------------------------------

        retry_issues = context.get("retry_issues")

        retry_corrections = context.get("retry_corrections")

        if retry_issues or retry_corrections:
            retry_payload = {
                "issues": retry_issues or [],
                "corrections": retry_corrections or [],
            }

            sections.append(
                self._section(
                    "Correcciones de una ejecución anterior",
                    self._serialize(retry_payload),
                )
            )

        # ------------------------------------------------------
        # Execution evidence
        # ------------------------------------------------------

        execution = context.get("execution")

        if execution:
            sections.append(
                self._section(
                    "Evidencia de ejecución",
                    self._serialize(execution),
                )
            )

        # ------------------------------------------------------
        # Additional instructions
        # ------------------------------------------------------

        additional_instructions = context.get("additional_instructions")

        if additional_instructions:
            sections.append(
                self._section(
                    "Instrucciones adicionales",
                    str(additional_instructions),
                )
            )

        # ------------------------------------------------------
        # Final instructions
        # ------------------------------------------------------

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
            sections.append(
                self._section(
                    "Instrucciones finales",
                    """
Realiza la tarea utilizando únicamente la información disponible.

Cuando debas analizar una implementación:

1. identifica primero los hechos observables;
2. separa las inferencias de los hechos;
3. indica explícitamente qué información no puede determinarse;
4. evita completar huecos con suposiciones;
5. respeta las restricciones del ExecutionPlan;
6. si existe información de retry, corrige específicamente los problemas
   señalados sin introducir cambios no justificados.

La respuesta debe ser concreta, técnica y específica para el proyecto.
""".strip(),
                )
            )

        return "\n\n".join(section.strip() for section in sections if section and section.strip())

    # ==========================================================
    # Section helper
    # ==========================================================

    @staticmethod
    def _section(
        title: str,
        content: str,
    ) -> str:
        return f"""
## {title}

{content}
""".strip()

    # ==========================================================
    # Truncation
    # ==========================================================

    def _truncate_prompt(
        self,
        prompt: str,
    ) -> str:
        limit = self.max_context_chars

        if len(prompt) <= limit:
            return prompt

        notice = (
            "\n\n[SYSTEM NOTICE]\n"
            "El contexto fue reducido por límite de tamaño. "
            "No inferir información ausente."
        )

        marker = "## Contexto y evidencia disponible"

        context_index = prompt.find(marker)

        if context_index != -1:
            before = prompt[:context_index]

            final_marker = "\n## Instrucciones finales"

            final_index = prompt.find(
                final_marker,
                context_index,
            )

            after = prompt[final_index:] if final_index != -1 else ""

            available = limit - len(before) - len(after) - len(notice)

            if available > 0:
                context_content = prompt[context_index + len(marker) :].strip()

                if len(context_content) > available:
                    context_content = context_content[:available] + "\n[CONTEXTO REDUCIDO]"

                result = before + marker + "\n\n" + context_content + after + notice

                return result[:limit]

        return (
            prompt[
                : max(
                    0,
                    limit - len(notice),
                )
            ]
            + notice
        )

    # ==========================================================
    # Inspection
    # ==========================================================

    def get_max_context_chars(self) -> int:
        return self.max_context_chars
