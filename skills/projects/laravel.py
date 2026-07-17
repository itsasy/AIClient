from skills.base import Skill
from skills.tools.shell import ShellTool

class LaravelProjectSkill(Skill):
    name = "laravel_project"
    description = "Crea proyecto Laravel completo con Docker"

    def execute(self, name: str = "mi_proyecto", **kwargs):
        shell = ShellTool()
        
        commands = [
            f"laravel new {name} --pest",
            f"cd {name} && php artisan make:auth",
            f"cd {name} && docker compose up -d",
        ]

        results = []
        for cmd in commands:
            result = shell.execute(cmd)
            results.append(result)

        return {
            "type": "project_creation",
            "payload": {
                "framework": "laravel",
                "name": name,
                "commands_executed": results,
            }
        }
EOF