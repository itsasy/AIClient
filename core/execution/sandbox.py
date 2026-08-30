from pathlib import Path
from typing import List, Dict

class ExecutionSandbox:
    def __init__(self, target_root: Path):
        self.target_root = Path(target_root).resolve()
        self.forbidden_patterns = [".env", "credentials", "secrets", ".git", ".aiclient", "core/skills/", "core/execution/"]
        
    def _is_forbidden(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.target_root)
            path_str = str(rel).replace("\\", "/")
            if "../" in path_str:
                return True
            for pattern in self.forbidden_patterns:
                if pattern in path_str:
                    return True
            return False
        except ValueError:
            return True # Not relative to target root

    def authorize_operation(self, capability: str, operation: str, sources: List[str], destinations: List[str]) -> str:
        # P15: Capability -> Operation Enforcement
        capability_map = {
            "move_files": ["move_files"],
            "copy_files": ["copy_files"],
            "rename_files": ["rename_files"],
            "rewrite_declared_imports": ["rewrite_declared_imports", "rewrite_imports"],
            "create_declared_adapter": ["create_declared_adapter"]
        }
        
        if operation in ("subprocess", "os.system", "shell", "eval", "exec"):
            return "REJECTED: Shell escalation"
            
        allowed_ops = capability_map.get(capability, [])
        if operation not in allowed_ops:
            return f"REJECTED: Capability {capability} does not allow operation {operation}"
            
        for s in sources:
            if s and self._is_forbidden(self.target_root / s):
                return "REJECTED: Forbidden source path"
                
        for d in destinations:
            if d and self._is_forbidden(self.target_root / d):
                return "REJECTED: Forbidden destination path"
                
        return "READY"
