from skills.base import Skill
from skills.tools.shell import ShellTool


class FullProjectGeneratorSkill(Skill):
    name = "full_project"
    description = "Genera y configura proyecto completo"

    def execute(self, framework: str = "laravel", name: str = "mi_proyecto", **kwargs):
        shell = ShellTool()

        if framework == "laravel":
            commands = [
                f"laravel new {name} --pest",
                f"cd {name} && composer require laravel/sanctum",
                f"cd {name} && php artisan sanctum:install",
                f"cd {name} && docker compose up -d --build",
            ]
        else:
            commands = [f"echo 'Framework {framework} no soportado aún'"]

        results = [shell.execute(cmd) for cmd in commands]

        return {
            "type": "full_project",
            "payload": {
                "framework": framework,
                "name": name,
                "results": results,
            },
        }
