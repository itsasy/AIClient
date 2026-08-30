import json
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import os

@dataclass
class WALEntry:
    transaction_id: str
    workflow_hash: str
    operation_hash: str
    operation_index: int
    operation_type: str
    status: str
    source: str = ""
    destination: str = ""
    expected_source_hash: str = ""
    expected_destination_hash: str = ""
    timestamp: float = 0.0
    previous_event_hash: str = ""
    event_hash: str = ""
    proposal_hash: str = ""
    specification_hash: str = ""
    graph_hash: str = ""
    
    def calculate_hash(self) -> str:
        payload = f"{self.transaction_id}:{self.proposal_hash}:{self.specification_hash}:{self.graph_hash}:{self.workflow_hash}:{self.operation_hash}:{self.operation_index}:{self.operation_type}:{self.status}:{self.source}:{self.destination}:{self.expected_source_hash}:{self.expected_destination_hash}:{self.timestamp}:{self.previous_event_hash}"
        return hashlib.sha256(payload.encode()).hexdigest()

class WriteAheadLog:
    def __init__(self, target_root: str):
        self.wal_path = Path(target_root) / ".aiclient_wal" / "journal.jsonl"
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = ""
        self._load_last_hash()
        
    def _load_last_hash(self):
        if not self.wal_path.exists():
            return
        try:
            with open(self.wal_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    self.last_hash = last_entry.get("event_hash", "")
        except Exception:
            pass

    def append(self, entry: WALEntry):
        entry.timestamp = time.time()
        entry.previous_event_hash = self.last_hash
        entry.event_hash = entry.calculate_hash()
        self.last_hash = entry.event_hash
        
        # O_APPEND guarantees atomic writes (if payload is small enough)
        with open(self.wal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.__dict__) + "\n")
            
    def get_entries(self, transaction_id: str) -> List[WALEntry]:
        if not self.wal_path.exists():
            return []
            
        entries = []
        with open(self.wal_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("transaction_id") == transaction_id:
                        entries.append(WALEntry(**data))
                except json.JSONDecodeError:
                    continue
        return entries
