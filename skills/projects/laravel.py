from skills.base import Skill
from skills.tools.shell import ShellTool


class LaravelProjectSkill(Skill):
    name = "laravel_project"
    description = "Crea proyecto Laravel completo con Docker y Sanctum"

    def execute(self, name: str = "mi_proyecto", **kwargs):
        # Extraer el nombre del proyecto de la consulta (si viene en el payload)
        if " " in name:
            name = name.split()[-1]
        if not name:
            name = "mi_proyecto"

        shell = ShellTool()

        # 1. Intentar crear el proyecto con Composer
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
            results.append((cmd, res))
            # Si algún comando falla, detener la ejecución
            if not res.get("payload", {}).get("ok"):
                # Verificar si el error es por "composer not found"
                output = res.get("payload", {}).get("output", "")
                if (
                    "command not found" in output.lower()
                    or "permission denied" in output.lower()
                ):
                    # Añadir mensaje de ayuda
                    results.append(
                        (
                            "help",
                            {
                                "payload": {
                                    "ok": False,
                                    "output": (
                                        "❌ Composer no encontrado en el sistema.\n"
                                        "Por favor, instala Composer en tu WSL con:\n"
                                        "  sudo apt update && sudo apt install composer\n"
                                        "O descarga el instalador oficial desde https://getcomposer.org/"
                                    ),
                                }
                            },
                        )
                    )
                break

        # Construir salida
        outputs = []
        all_ok = True
        for cmd, res in results:
            if cmd == "help":
                outputs.append(res.get("payload", {}).get("output", ""))
                all_ok = False
                break
            ok = res.get("payload", {}).get("ok", False)
            output = res.get("payload", {}).get("output", "")
            outputs.append(f"$ {cmd}\n{output}")
            if not ok:
                all_ok = False
                break

        return {
            "type": "laravel_result",
            "payload": {
                "ok": all_ok,
                "project_name": name,
                "output": "\n\n".join(outputs)[:3000],
            },
        }
