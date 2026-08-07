from __future__ import annotations

import re
import shutil

from pathlib import Path
from typing import Any

from core.config import Config

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from core.tools.shell import ShellTool

from skills.base import Skill


class LaravelProjectSkill(Skill):

    name = "laravel_project"

    description = "Crea proyecto Laravel completo con Docker y Sanctum."

    version = "2.0"

    capabilities = (
        "laravel_generation",
        "docker_setup",
        "sanctum_configuration",
        "shell_execution",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        name = params.get(
            "name",
            "mi_proyecto",
        )

        force = params.get(
            "force",
            False,
        )

        if " " in name:

            name = name.split()[-1]

        if not name:

            name = "mi_proyecto"

        if not re.match(
            r"^[a-zA-Z0-9_-]+$",
            name,
        ):

            return {
                "ok": False,
                "result": None,
                "error": (
                    f"Nombre de proyecto inválido: '{name}'. "
                    "Usa letras, números, guiones y guiones bajos."
                ),
            }

        shell = ShellTool()

        project_path = Path.cwd() / name

        if project_path.exists():

            if not force:

                return {
                    "ok": False,
                    "result": {
                        "project_name": name,
                    },
                    "error": (
                        f"El directorio '{name}' ya existe. " "Usa force=True para reemplazarlo."
                    ),
                }

            try:

                shutil.rmtree(
                    project_path,
                )

            except Exception as exc:

                return {
                    "ok": False,
                    "result": None,
                    "error": str(exc),
                }

        commands = [
            f"composer create-project laravel/laravel {name}",
            (f"cd {name} && " "./vendor/bin/sail install " "--with=mysql,redis --no-interaction"),
            (f"cd {name} && " "./vendor/bin/sail up -d"),
            (f"cd {name} && " "./vendor/bin/sail composer require laravel/sanctum"),
            (f"cd {name} && " "./vendor/bin/sail artisan migrate"),
        ]

        results = []

        timeout = Config.LARAVEL_TIMEOUT

        for command in commands:

            result = shell.execute(
                command,
                timeout=timeout,
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
                "type": "laravel_result",
                "payload": {
                    "project_name": name,
                    "results": results,
                },
            },
            "error": (None if success else "Falló la creación del proyecto Laravel."),
        }
