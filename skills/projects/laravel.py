import shutil
import re
from pathlib import Path
from skills.base import Skill
from skills.tools.shell import ShellTool
from core.config import Config


class LaravelProjectSkill(Skill):
    name = "laravel_project"
    description = "Crea proyecto Laravel completo con Docker y Sanctum"

    def execute(self, name: str = "mi_proyecto", force: bool = False, **kwargs):
        # Limpieza y validación del nombre
        if " " in name:
            name = name.split()[-1]
        if not name:
            name = "mi_proyecto"

        # Seguridad: solo caracteres permitidos (evita inyección de comandos)
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            return {
                "type": "laravel_result",
                "payload": {
                    "ok": False,
                    "project_name": name,
                    "output": (
                        f"❌ Nombre de proyecto inválido: '{name}'. "
                        "Usa solo letras, números, guiones y guiones bajos."
                    ),
                },
            }

        shell = ShellTool()
        project_path = Path.cwd() / name
        laravel_timeout = Config.LARAVEL_TIMEOUT

        # Seguridad CRÍTICA: no borrar sin consentimiento explícito
        if project_path.exists():
            if not force:
                return {
                    "type": "laravel_result",
                    "payload": {
                        "ok": False,
                        "project_name": name,
                        "output": (
                            f"⚠️ El directorio '{name}' ya existe.\n"
                            "Para borrarlo y crear uno nuevo, usa force=True.\n"
                            "O elimínalo manualmente y vuelve a intentar."
                        ),
                    },
                }

            # Solo llegamos aquí si force=True (uso consciente)
            try:
                shutil.rmtree(project_path)
                output_warning = f"⚠️  Directorio '{name}' eliminado (force=True).\n"
            except Exception as e:
                return {
                    "type": "laravel_result",
                    "payload": {
                        "ok": False,
                        "project_name": name,
                        "output": f"❌ No se pudo eliminar el directorio '{name}': {e}",
                    },
                }
        else:
            output_warning = ""

        commands = [
            f"composer create-project laravel/laravel {name}",
            f"cd {name} && php artisan sail:install --with=mysql,redis --no-interaction",
            f"cd {name} && ./vendor/bin/sail up -d",
            f"cd {name} && ./vendor/bin/sail composer require laravel/sanctum",
            f"cd {name} && ./vendor/bin/sail artisan vendor:publish --provider='Laravel\\Sanctum\\SanctumServiceProvider' --no-interaction",
            f"cd {name} && ./vendor/bin/sail artisan migrate",
        ]

        results = []
        for cmd in commands:
            res = shell.execute(cmd, timeout=laravel_timeout)
            results.append((cmd, res))

            if not res.get("payload", {}).get("ok"):
                output = res.get("payload", {}).get("output", "")
                if (
                    "command not found" in output.lower()
                    or "permission denied" in output.lower()
                ):
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

        outputs = [output_warning] if output_warning else []
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

        if all_ok:
            final_message = (
                f"✅ **Proyecto Laravel '{name}'** creado y configurado correctamente."
            )
        else:
            if project_path.exists() and not all_ok:
                final_message = (
                    f"⚠️ **Proyecto Laravel '{name}'** creado, pero fallaron pasos posteriores.\n"
                    "El proyecto está disponible, pero es posible que Sail, Sanctum o la migración no se hayan configurado correctamente."
                )
            else:
                final_message = f"❌ **Proyecto Laravel** falló al crearse."

        return {
            "type": "laravel_result",
            "payload": {
                "ok": all_ok,
                "project_name": name,
                "output": final_message + "\n\n" + "\n\n".join(outputs)[:3000],
            },
        }
