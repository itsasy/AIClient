from __future__ import annotations

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
    Skill para crear proyectos completos en diferentes stacks.

    Soporte:
        - Laravel (composer create-project)
        - React (npx create-react-app)
        - Vue (npm create vue@latest)
        - Django (django-admin startproject)
        - Next.js (npx create-next-app)
        - Flutter (flutter create)

    Responsabilidades:
        - Validar nombre del proyecto (caracteres seguros).
        - Ejecutar comandos específicos por framework.
        - Usar PathPolicy para verificar la ruta de destino.
        - Usar SecurityPolicy para controlar permisos.

    No:
        - Genera contenido.
        - Llama al LLM.
        - Decide qué framework usar (lo recibe del plan).
    """

    name = "create_project"
    description = "Crea un proyecto completo en el stack especificado."
    version = "2.0"
    capabilities = (
        "project_generation",
        "laravel",
        "react",
        "vue",
        "django",
        "nextjs",
        "flutter",
    )

    # Mapeo de framework a comando y estrategia
    FRAMEWORK_COMMANDS = {
        "laravel": {
            "command": "composer create-project laravel/laravel {name}",
            "post_commands": [
                "cd {name} && php artisan sail:install --with=mysql,redis --no-interaction",
            ],
            "dependency": "composer",
            "validate": lambda name: True,  # composer valida por sí mismo
        },
        "react": {
            "command": "npx create-react-app {name}",
            "post_commands": [],
            "dependency": "npx",
            "validate": lambda name: True,
        },
        "vue": {
            "command": "npm create vue@latest {name}",
            "post_commands": [
                "cd {name} && npm install",
            ],
            "dependency": "npm",
            "validate": lambda name: True,
        },
        "django": {
            "command": "django-admin startproject {name}",
            "post_commands": [
                "cd {name} && python manage.py runserver",
            ],
            "dependency": "django-admin",
            "validate": lambda name: True,
        },
        "nextjs": {
            "command": "npx create-next-app@latest {name}",
            "post_commands": [],
            "dependency": "npx",
            "validate": lambda name: True,
        },
        "flutter": {
            "command": "flutter create {name}",
            "post_commands": [],
            "dependency": "flutter",
            "validate": lambda name: True,
        },
    }

    # Caracteres permitidos para nombres de proyecto
    ALLOWED_NAME_PATTERN = r"^[a-zA-Z0-9_\-]+$"

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Crea un proyecto según el framework y nombre especificados.
        """
        params = step.params or {}

        framework = params.get("framework", "").strip().lower()
        name = params.get("name", "").strip()
        options = params.get("options", {})

        # 1. Validar framework soportado
        if framework not in self.FRAMEWORK_COMMANDS:
            return self._error(
                f"Framework '{framework}' no soportado. "
                f"Soportados: {', '.join(sorted(self.FRAMEWORK_COMMANDS.keys()))}"
            )

        # 2. Validar nombre del proyecto
        if not name:
            return self._error("No se proporcionó un nombre para el proyecto.")

        import re

        if not re.match(self.ALLOWED_NAME_PATTERN, name):
            return self._error(
                f"Nombre de proyecto inválido: '{name}'. "
                "Usa solo letras, números, guiones y guiones bajos."
            )

        # 3. Validar seguridad de la ruta de destino
        target_dir = Config.TARGET_PROJECT_ROOT / name
        ok, error = SecurityPolicy.check_path(str(target_dir), plan)
        if not ok:
            return self._error(error)

        # 4. Verificar política de escritura
        if not plan.allows_write():
            return self._error("Política de escritura no permitida en este plan.")

        # 5. Verificar si el directorio ya existe
        if target_dir.exists():
            return self._error(
                f"El directorio '{name}' ya existe en {target_dir.parent}. "
                "Elimínalo o elige otro nombre."
            )

        # 6. Verificar dependencia necesaria
        dependency = self.FRAMEWORK_COMMANDS[framework]["dependency"]
        if not self._check_dependency(dependency):
            return self._error(
                f"La dependencia '{dependency}' no está disponible en el sistema. "
                f"Instálala antes de crear un proyecto {framework}."
            )

        # 7. Ejecutar la creación
        results = self._execute_framework(framework, name, target_dir)

        # 8. Ejecutar comandos post-creación
        post_results = self._execute_post_commands(framework, name)

        # 9. Componer resultado
        return {
            "ok": True,
            "result": {
                "type": "project_creation",
                "framework": framework,
                "name": name,
                "path": str(target_dir),
                "commands": results,
                "post_commands": post_results,
            },
            "error": None,
        }

    # ==========================================================
    # Helpers
    # ==========================================================

    def _check_dependency(self, dependency: str) -> bool:
        """Verifica si un comando está disponible en el sistema."""
        try:
            # Verificar si el comando existe en el PATH
            subprocess.run(
                ["which", dependency],
                capture_output=True,
                timeout=2,
                check=False,
            )
            return True
        except Exception:
            return False

    def _execute_command(self, command: str, cwd: Path | None = None) -> dict[str, Any]:
        """Ejecuta un comando shell de forma segura."""
        start = time.time()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=Config.SHELL_TIMEOUT,
                cwd=cwd or Config.TARGET_PROJECT_ROOT,
                check=False,
            )

            duration = round(time.time() - start, 3)

            output = result.stdout.strip() or result.stderr.strip() or ""

            return {
                "ok": result.returncode == 0,
                "command": command,
                "output": output[:1500],
                "returncode": result.returncode,
                "duration": duration,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "command": command,
                "error": f"Timeout ({Config.SHELL_TIMEOUT}s)",
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
        target_dir: Path,
    ) -> list[dict[str, Any]]:
        """Ejecuta el comando principal para el framework."""
        command_template = self.FRAMEWORK_COMMANDS[framework]["command"]
        command = command_template.format(name=name)

        results = [self._execute_command(command)]

        return results

    def _execute_post_commands(
        self,
        framework: str,
        name: str,
    ) -> list[dict[str, Any]]:
        """Ejecuta comandos post-creación dentro del proyecto."""
        post_commands = self.FRAMEWORK_COMMANDS[framework].get("post_commands", [])
        results = []

        project_dir = Config.TARGET_PROJECT_ROOT / name

        for cmd_template in post_commands:
            command = cmd_template.format(name=name)
            result = self._execute_command(command, cwd=project_dir)
            results.append(result)

        return results

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "ok": False,
            "result": None,
            "error": message,
        }
