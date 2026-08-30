import shutil
from pathlib import Path
from typing import List, Dict
import hashlib
import os

class RollbackManager:
    def __init__(self, target_root: Path, transaction_id: str):
        self.target_root = target_root
        self.transaction_id = transaction_id
        self.backup_dir = self.target_root / ".aiclient_backup" / self.transaction_id
        self.snapshots: Dict[str, str] = {} # rel_path -> hash
        self.new_files: List[str] = [] # rel_paths of files created during transaction
        
    def _hash_file(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()
        
    def snapshot(self, rel_paths: List[str]):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        for rel in rel_paths:
            src = self.target_root / rel
            if src.exists() and src.is_file():
                self.snapshots[rel] = self._hash_file(src)
                dest = self.backup_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                
    def record_new_file(self, rel_path: str):
        self.new_files.append(rel_path)
                
    def rollback(self) -> bool:
        success = True
        # Restore pre-existing files
        for rel, original_hash in self.snapshots.items():
            backup_file = self.backup_dir / rel
            target_file = self.target_root / rel
            
            if backup_file.exists():
                # Check for concurrent modification (if it changed from our mutation, it's fine, but if it doesn't match original and doesn't match what we did? In a real system we'd track post-mutation hash too. For now we force restore).
                target_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(backup_file, target_file)
                except Exception:
                    success = False
            else:
                success = False
                
        # Remove newly created files (that didn't exist in snapshot)
        for rel in self.new_files:
            target_file = self.target_root / rel
            if target_file.exists() and rel not in self.snapshots:
                try:
                    os.remove(target_file)
                    # Clean up empty parent dirs if possible
                    try:
                        target_file.parent.rmdir()
                    except OSError:
                        pass
                except OSError:
                    success = False
                    
        return success
        
    def cleanup(self):
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir, ignore_errors=True)
