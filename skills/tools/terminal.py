from skills.base import Skill
import subprocess
from pathlib import Path

class TerminalSkill(Skill):
    name = "terminal"
    description = "Ejecuta comandos seguros en terminal"
    
    ALLOWED_COMMANDS = ["ls", "tree", "git status", "git log --oneline -5", "pwd", "find"]
    
    def execute(self, command: str, **kwargs) -> str:
        # Seguridad básica
        if not any(cmd in command for cmd in self.ALLOWED_COMMANDS):
            return "Comando no permitido por seguridad."
        
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            return f"Salida:\n{result.stdout}\nError:\n{result.stderr}"
        except Exception as e:
            return f"Error ejecutando comando: {str(e)}"
