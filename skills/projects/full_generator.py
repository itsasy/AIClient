from skills.base import Skill
from skills.tools.shell import ShellTool


class FullProjectGeneratorSkill(Skill):
    name = "full_project"
    description = "Genera y configura proyecto completo"

    def execute(self, framework: str = "laravel", name: str = "mi_proyecto", **kwargs):
        shell = ShellTool()

        if framework == "laravel":
            commands = [
                f"composer create-project laravel/laravel {name}",
                f"cd {name} && php artisan sail:install --with=mysql,redis",
                f"cd {name} && ./vendor/bin/sail up -d",
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
