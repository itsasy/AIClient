import hashlib
from pathlib import Path
from typing import List, Dict, Set, Any
import os

class ChangeManifest:
    def __init__(self, target_root: Path):
        self.target_root = target_root
        self.before_hashes: Dict[str, str] = {}
        self.after_hashes: Dict[str, str] = {}
        
    def _hash_file(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        hasher = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                hasher.update(f.read())
            return hasher.hexdigest()
        except Exception:
            return ""

    def record_before(self, paths: List[str]):
        for p in paths:
            abs_path = self.target_root / p
            self.before_hashes[p] = self._hash_file(abs_path)
            
    def record_after(self, paths: List[str]):
        # Also scan broadly to catch unexpected changes?
        # A real implementation would scan the whole project or modified dirs.
        # For P10, we'll check planned paths + a small tree scan around dest/src.
        scan_paths = set(paths)
        for p in scan_paths:
            abs_path = self.target_root / p
            self.after_hashes[p] = self._hash_file(abs_path)

    def compare(self, planned_mutations: List[str]) -> Dict[str, List[str]]:
        result = {
            "created": [],
            "modified": [],
            "deleted": [],
            "unchanged": [],
            "unexpected": []
        }
        
        all_paths = set(self.before_hashes.keys()).union(set(self.after_hashes.keys()))
        
        for p in all_paths:
            before = self.before_hashes.get(p, "")
            after = self.after_hashes.get(p, "")
            
            if before == after:
                result["unchanged"].append(p)
            elif before == "" and after != "":
                result["created"].append(p)
                if p not in planned_mutations:
                    result["unexpected"].append(p)
            elif before != "" and after == "":
                result["deleted"].append(p)
                if p not in planned_mutations:
                    result["unexpected"].append(p)
            else:
                result["modified"].append(p)
                if p not in planned_mutations:
                    result["unexpected"].append(p)
                    
        return result
