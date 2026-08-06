from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from core.tools.shell import ShellTool

from skills.base import Skill


class FullProjectGeneratorSkill(Skill):

    name = "full_project"

    description = "Genera y configura proyecto completo."

    version = "2.0"

    capabilities = (
        "project_generation",
        "framework_setup",
        "shell_execution",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        framework = params.get(
            "framework",
            "laravel",
        )

        name = params.get(
            "name",
            "mi_proyecto",
        )

        shell = ShellTool()

        if framework == "laravel":

            commands = [
                f"composer create-project laravel/laravel {name}",
                (f"cd {name} && " "php artisan sail:install --with=mysql,redis"),
                (f"cd {name} && " "./vendor/bin/sail up -d"),
            ]

        elif framework == "react":

            commands = [
                f"npx create-react-app {name}",
                f"cd {name} && npm start",
            ]

        elif framework == "vue":

            commands = [
                f"npm create vue@latest {name}",
                f"cd {name} && npm install",
            ]

        elif framework == "django":

            commands = [
                f"django-admin startproject {name}",
                f"cd {name} && python manage.py runserver",
            ]

        else:

            commands = [
                f"echo 'Framework {framework} no soportado aún'",
            ]

        results = []

        for command in commands:

            result = shell.execute(
                command,
            )

            results.append(
                {
                    "command": command,
                    "result": result,
                }
            )

            if not result.get(
                "ok",
                False,
            ):

                break

        success = all(
            item["result"].get(
                "ok",
                False,
            )
            for item in results
        )

        return {
            "ok": success,
            "result": {
                "type": "full_project",
                "payload": {
                    "framework": framework,
                    "name": name,
                    "results": results,
                },
            },
            "error": (None if success else "Falló la generación del proyecto."),
        }
