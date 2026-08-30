import os
import json
import time
from pathlib import Path

class StateLock:
    def __init__(self, target_root: Path, transaction_id: str):
        self.target_root = target_root
        self.lock_file = Path(target_root) / ".aiclient.lock"
        self.transaction_id = transaction_id
        
    def acquire(self, timeout: int = 5) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'w') as f:
                    json.dump({
                        "transaction_id": self.transaction_id,
                        "process_id": os.getpid(),
                        "timestamp": time.time(),
                        "target_root": str(self.target_root)
                    }, f)
                return True
            except FileExistsError:
                # Basic orphan detection: check if process is running (very naive on Windows)
                if self._is_orphaned():
                    self.release()
                    continue
                time.sleep(0.5)
        return False
        
    def _is_orphaned(self) -> bool:
        try:
            with open(self.lock_file, "r") as f:
                data = json.load(f)
            pid = data.get("process_id")
            # In python on windows, os.kill isn't a great process check but we can test if it's our own old lock
            # A real implementation might use psutil. For now we just return False unless it's very old.
            if time.time() - data.get("timestamp", 0) > 300: # 5 min timeout
                return True
        except Exception:
            pass
        return False

    def release(self):
        try:
            if self.lock_file.exists():
                os.remove(self.lock_file)
        except OSError:
            pass
