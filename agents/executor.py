import logging
from agents.base import Agent
from llm.router import LLMRouter
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):
    name = "executor"
    role = "Ejecutor Autónomo de Tareas"

    AVAILABLE_SKILLS = {
        "shell",
        "docker",
        "execute_code",
        "sandbox",
        "laravel_project",
        "full_project",
        "write_file",
    }

    def __init__(self):
        self.skill_manager = SkillManager()

    def process(
        self,
        task: str,
        context: dict[str, object] | None = None,
        skill_name: str | None = None,
        skill_params: dict[str, object] | None = None,
    ) -> str:
        if not skill_name or skill_name not in self.AVAILABLE_SKILLS:
            return LLMRouter.generate(
                task=task,
                context=context if context is not None else {},
                skill_name=skill_name,
                skill_params=skill_params,
            )

        logger.info(
            "Ejecutando skill %s",
            skill_name,
        )

        result = self.skill_manager.execute(
            skill_name,
            **(skill_params if skill_params is not None else {}),
        )
        
        result_type = result.get("type")

        if result_type in {
            "shell_result",
            "docker_result",
            "execution_result",
            "sandbox_result",
        }:
            return self._format_execution_result(
                skill_name,
                result.get("payload", {}),
            )

        if result_type == "laravel_result":
            return self._format_laravel_result(
                result.get("payload", {}),
            )

        if result_type == "write_file_result":
            return self._format_write_file_result(result.get("payload", {}))

        return str(result)

    def _format_execution_result(
        self,
        skill_name: str,
        payload: dict,
    ) -> str:
        if payload.get("ok"):
            output = payload.get(
                "output",
                "Comando ejecutado correctamente (sin salida).",
            )
            return f"✅ **{skill_name}** ejecutado:\n```\n{output}\n```"

        error = (
            payload.get("message")
            or payload.get("output")
            or payload.get("error")
            or "Error desconocido."
        )

        return f"❌ **{skill_name}** falló:\n```\n{error}\n```"

    def _format_laravel_result(
        self,
        payload: dict,
    ) -> str:
        project_name = payload.get("project_name", "proyecto")
        output = payload.get("output", "")

        if payload.get("ok"):
            return (
                f"✅ **Proyecto Laravel '{project_name}'** creado correctamente.\n\n"
                f"Salida:\n```\n{output}\n```"
            )

        return (
            "❌ **Proyecto Laravel** falló al crearse.\n\n" f"Salida de error:\n```\n{output}\n```"
        )

    def _format_write_file_result(
        self,
        payload: dict,
    ) -> str:
        if payload.get("ok"):
            return "✅ Archivo creado correctamente.\n\n" f"Ruta: {payload.get('path')}"

        return "❌ No se pudo crear el archivo.\n\n" f"Error: {payload.get('error')}"
