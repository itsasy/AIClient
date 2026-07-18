from skills.base import Skill
from skills.tools.shell import ShellTool


class LaravelProjectSkill(Skill):
    name = "laravel_project"
    description = "Crea proyecto Laravel completo con Docker y Sanctum"

    def execute(self, name: str = "mi_proyecto", **kwargs):
        if " " in name:
            name = name.split()[-1]
        if not name:
            name = "mi_proyecto"

        shell = ShellTool()
        commands = [
            f"composer create-project laravel/laravel {name}",
            f"cd {name} && php artisan sail:install --with=mysql,redis",
            f"cd {name} && ./vendor/bin/sail up -d",
            f"cd {name} && ./vendor/bin/sail composer require laravel/sanctum",
            f"cd {name} && ./vendor/bin/sail artisan vendor:publish --provider='Laravel\\Sanctum\\SanctumServiceProvider'",
            f"cd {name} && ./vendor/bin/sail artisan migrate",
        ]

        results = []
        for cmd in commands:
            res = shell.execute(cmd)
            results.append(res)

        ok = all(res.get("payload", {}).get("ok", False) for res in results)
        outputs = "\n\n".join(
            [
                f"$ {cmd}\n{res.get('payload', {}).get('output', '')}"
                for cmd, res in zip(commands, results)
            ]
        )

        return {
            "type": "laravel_result",
            "payload": {
                "ok": ok,
                "project_name": name,
                "output": outputs[:2000],
            },
        }
