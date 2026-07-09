from skills.base import Skill
import subprocess
from pathlib import Path

class ShellTool(Skill):
    name = "shell"
    description = "Ejecuta comandos seguros"
    
    # Lista blanca estricta
    SAFE_PREFIXES = ["git ", "ls", "tree ", "pwd", "echo ", "cat ", "find ", "grep "]
    SAFE_EXACT = ["git status", "git log --oneline -10", "git branch"]
    
    def execute(self, command: str, **kwargs) -> str:
        command = command.strip()
        
        # Validación de seguridad
        if not any(command.startswith(prefix) for prefix in self.SAFE_PREFIXES) and command not in self.SAFE_EXACT:
            return "❌ Comando bloqueado por seguridad."
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=12,
                cwd=Path("/home/alexis/Workspace")
            )
            output = result.stdout.strip() or result.stderr.strip()
            return f"Comando: `{command}`\n\n{output[:1200]}"
        except subprocess.TimeoutExpired:
            return "⏰ Comando timeout (demasiado lento)"
        except Exception as e:
            return f"❌ Error: {str(e)}"
