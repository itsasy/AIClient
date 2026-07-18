from agents.base import Agent
from skills.manager import SkillManager


class ExecutorAgent(Agent):
    name = "executor"
    role = "Ejecutor Autónomo de Tareas"

    def process(
        self,
        task: str,
        context: dict | None = None,
        skill_name: str | None = None,
        skill_params: dict | None = None,
    ) -> str:
        if not skill_name or skill_name not in (
            "shell",
            "docker",
            "execute_code",
            "sandbox",
            "laravel_project",
            "full_project",
        ):
            from llm.router import LLMRouter

            return LLMRouter.generate(
                task=task,
                context=context or {},
                skill_name=skill_name,
                skill_params=skill_params,
            )

        skill_manager = SkillManager()
        result = skill_manager.execute(skill_name, **(skill_params or {}))

        if result.get("type") in (
            "shell_result",
            "docker_result",
            "execution_result",
            "sandbox_result",
        ):
            payload = result.get("payload", {})
            if payload.get("ok"):
                output = payload.get(
                    "output", "Comando ejecutado correctamente (sin salida)."
                )
                return f"✅ **{skill_name}** ejecutado:\n```\n{output}\n```"
            else:
                error = (
                    payload.get("message")
                    or payload.get("output")
                    or payload.get("error")
                    or "Error desconocido."
                )
                return f"❌ **{skill_name}** falló:\n```\n{error}\n```"

        return str(result)
