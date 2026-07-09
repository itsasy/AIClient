from skills.base import Skill
import subprocess

class GitTool(Skill):
    name = "git"
    description = "Operaciones Git seguras"
    
    def execute(self, action: str = "status", **kwargs) -> str:
        commands = {
            "status": "git status",
            "log": "git log --oneline -10",
            "branch": "git branch",
            "diff": "git diff HEAD~1",
        }
        cmd = commands.get(action, "git status")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return f"Git {action}:\n{result.stdout or result.stderr}"
        except Exception as e:
            return f"Error Git: {str(e)}"
