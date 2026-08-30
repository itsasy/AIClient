from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import json
from pathlib import Path
import os

@dataclass
class ExecutionAction:
    action_id: str
    transaction_id: str
    candidate: str
    operation: str
    source: List[str]
    destination: List[str]
    policy_decision: str
    approval_required: bool
    approval_status: str
    capability: str
    reversible: bool = True
    verification_required: List[str] = field(default_factory=list)

@dataclass
class ExecutionRecord:
    transaction_id: str
    target_root: str
    candidate: str
    task: str = ""
    mode: str = "DRY_RUN"
    status: str = "PLANNED"  # PLANNED, APPROVED, EXECUTING, VERIFYING, COMMITTED, ROLLING_BACK, ROLLED_BACK, FAILED, RECOVERY_REQUIRED, ROLLBACK_FAILED
    actions: List[ExecutionAction] = field(default_factory=list)
    files_planned: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    verification_results: Dict[str, str] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamps: Dict[str, float] = field(default_factory=lambda: {"created": time.time()})
    
    def persist(self):
        target = Path(self.target_root)
        record_dir = target / ".aiclient_transactions"
        record_dir.mkdir(parents=True, exist_ok=True)
        record_path = record_dir / f"{self.transaction_id}.json"
        
        self.timestamps["updated"] = time.time()
        
        data = {
            "transaction_id": self.transaction_id,
            "target_root": self.target_root,
            "candidate": self.candidate,
            "task": self.task,
            "mode": self.mode,
            "status": self.status,
            "files_planned": self.files_planned,
            "files_changed": self.files_changed,
            "verification_results": self.verification_results,
            "manifest": self.manifest,
            "errors": self.errors,
            "timestamps": self.timestamps
        }
        
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load(target_root: Path, transaction_id: str) -> Optional['ExecutionRecord']:
        record_path = target_root / ".aiclient_transactions" / f"{transaction_id}.json"
        if not record_path.exists():
            return None
        with open(record_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        record = ExecutionRecord(
            transaction_id=data["transaction_id"],
            target_root=data["target_root"],
            candidate=data["candidate"],
            task=data.get("task", ""),
            mode=data["mode"],
            status=data["status"]
        )
        record.files_planned = data.get("files_planned", [])
        record.files_changed = data.get("files_changed", [])
        record.verification_results = data.get("verification_results", {})
        record.manifest = data.get("manifest", {})
        record.errors = data.get("errors", [])
        record.timestamps = data.get("timestamps", {})
        return record
