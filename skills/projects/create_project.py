from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from core.config import Config
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.tools.path_policy import PathPolicy
from core.tools.security_policy import SecurityPolicy
from skills.base import Skill


class CreateProjectSkill(Skill):
    """
    Crea proyectos en stacks conocidos.

    No genera contenido, no llama al LLM.
    Recibe framework/name del plan y materializa en disco.
    """

    name = "create_project"
    description = "Crea un proyecto completo en el stack especificado."
    version = "2.1"
    capabilities = (
        "project_generation",
        "laravel",
        "react",
        "vue",
        "django",
        "nextjs",
        "flutter",
    )

    FRAMEWORK_ALIASES = {
        "next": "nextjs",
        "next.js": "nextjs",
        "nextjs": "nextjs",
        "reactjs": "react",
        "react.js": "react",
        "vuejs": "vue",
        "vue.js": "vue",
        "nuxt": "vue",
        "django": "django",
        "laravel": "laravel",
        "flutter": "flutter",
        "react": "react",
        "vue": "vue",
    }

    FRAMEWORK_COMMANDS = {
        "laravel": {
            "command": "composer create-project laravel/laravel {name}",
            "post_commands": [],
            "dependency": "composer",
        },
        "react": {
            "command": "npx --yes create-react-app {name}",
            "post_commands": [],
            "dependency": "npx",
        },
        "vue": {
            "command": "npm create vue@latest {name} -- --default",
            "post_commands": [],
            "dependency": "npm",
        },
        "django": {
            "command": "django-admin startproject {name}",
            "post_commands": [],
            "dependency": "django-admin",
        },
        "nextjs": {
            "command": (
                "npx --yes create-next-app@latest {name} "
                '--ts --eslint --app --src-dir --import-alias "@/*" --use-npm --no-turbopack'
            ),
            "post_commands": [],
            "dependency": "npx",
        },
        "flutter": {
            "command": "flutter create {name}",
            "post_commands": [],
            "dependency": "flutter",
        },
    }

    ALLOWED_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-]*$")

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = step.params or {}

        framework = self._normalize_framework(params.get("framework", ""))
        name = str(params.get("name", "") or "").strip()

        if framework not in self.FRAMEWORK_COMMANDS:
            return self._error(
                f"Framework '{params.get('framework')}' no soportado. "
                f"Soportados: {', '.join(sorted(self.FRAMEWORK_COMMANDS.keys()))}"
            )

        if not name:
            return self._error("No se proporcionó un nombre para el proyecto.")

        if not self.ALLOWED_NAME_PATTERN.match(name):
            return self._error(
                f"Nombre de proyecto inválido: '{name}'. "
                "Debe empezar por letra y usar solo letras, números, - y _."
            )

        if not plan.allows_write():
            return self._error("Política de escritura no permitida en este plan.")

        target_dir = Path(Config.TARGET_PROJECT_ROOT) / name

        ok, error = SecurityPolicy.check_path(str(target_dir), plan)
        if not ok:
            return self._error(error or "Ruta de destino no permitida.")

        if not PathPolicy.is_within_project(target_dir):
            return self._error(
                f"Path traversal bloqueado: destino fuera del proyecto ({target_dir})."
            )

        if target_dir.exists():
            return self._error(f"El directorio '{name}' ya existe en {target_dir.parent}.")

        dependency = self.FRAMEWORK_COMMANDS[framework]["dependency"]
        if not self._check_dependency(dependency):
            return self._error(
                f"La dependencia '{dependency}' no está disponible. "
                f"Instálala antes de crear un proyecto {framework}."
            )

        main_result = self._execute_framework(framework, name, plan)
        if not main_result.get("ok"):
            return {
                "ok": False,
                "result": {
                    "type": "project_creation",
                    "framework": framework,
                    "name": name,
                    "path": str(target_dir),
                    "commands": [main_result],
                },
                "error": main_result.get("error")
                or main_result.get("output")
                or "Fallo al crear el proyecto.",
            }

        post_results = self._execute_post_commands(framework, name, plan)

        return {
            "ok": True,
            "result": {
                "type": "project_creation",
                "framework": framework,
                "name": name,
                "path": str(target_dir),
                "commands": [main_result],
                "post_commands": post_results,
            },
            "error": None,
        }

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _normalize_framework(self, value: Any) -> str:
        raw = str(value or "").strip().lower()
        return self.FRAMEWORK_ALIASES.get(raw, raw)

    def _check_dependency(self, dependency: str) -> bool:
        path = shutil.which(dependency)
        return path is not None

    def _execute_command(
        self,
        command: str,
        plan: ExecutionPlan,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        ok, err = SecurityPolicy.check_command(command, plan)
        if not ok:
            return {
                "ok": False,
                "command": command,
                "error": err,
                "output": "",
                "blocked": True,
            }

        start = time.time()
        timeout = getattr(Config, "SHELL_TIMEOUT", 300)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd or Config.TARGET_PROJECT_ROOT),
                check=False,
            )
            duration = round(time.time() - start, 3)
            output = (result.stdout or result.stderr or "").strip()

            return {
                "ok": result.returncode == 0,
                "command": command,
                "output": output[:2000],
                "returncode": result.returncode,
                "duration": duration,
                "error": None if result.returncode == 0 else output[:500],
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "command": command,
                "error": f"Timeout ({timeout}s)",
                "output": "",
            }
        except Exception as e:
            return {
                "ok": False,
                "command": command,
                "error": str(e),
                "output": "",
            }

    def _execute_framework(
        self,
        framework: str,
        name: str,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        template = self.FRAMEWORK_COMMANDS[framework]["command"]
        command = template.format(name=name)
        return self._execute_command(command, plan)

    def _execute_post_commands(
        self,
        framework: str,
        name: str,
        plan: ExecutionPlan,
    ) -> list[dict[str, Any]]:
        templates = self.FRAMEWORK_COMMANDS[framework].get("post_commands", [])
        project_dir = Path(Config.TARGET_PROJECT_ROOT) / name
        results: list[dict[str, Any]] = []

        for template in templates:
            command = template.format(name=name)
            # Si el template usa "cd X && ...", mejor correr en project_dir
            if command.startswith(f"cd {name}"):
                # ya usamos cwd=project_dir
                command = re.sub(rf"^cd\s+{re.escape(name)}\s+&&\s+", "", command)
            results.append(self._execute_command(command, plan, cwd=project_dir))

        return results

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "ok": False,
            "result": None,
            "error": message,
        }
