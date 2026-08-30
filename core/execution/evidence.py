import time
import uuid
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

@dataclass
class ExecutionEvidence:
    transaction_id: str
    target_root: str
    candidate: str
    workflow_hash: str
    policy_hash: str
    approval_hash: str
    boundary_hash: str
    
    actions_executed: List[str] = field(default_factory=list)
    manifest_hash: str = ""
    verification_results: Dict[str, str] = field(default_factory=dict)
    rollback_result: str = "NOT_REQUIRED"
    
    status: str = "COLLECTING"  # COLLECTING, COMPLETE, INVALID, INCOMPLETE
    final_status: str = "UNKNOWN"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    evidence_hash: str = ""

    def generate_hash(self) -> str:
        payload = {
            "tx": self.transaction_id,
            "workflow": self.workflow_hash,
            "policy": self.policy_hash,
            "approval": self.approval_hash,
            "manifest": self.manifest_hash,
            "verification": self.verification_results,
            "final_status": self.final_status
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class EvidenceManager:
    def __init__(self, target_root: Path):
        self.target_root = Path(target_root)
        self.evidence_dir = self.target_root / ".aiclient_evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def create(self, transaction_id: str, candidate: str, workflow_hash: str, policy_hash: str, approval_hash: str, boundary_hash: str) -> ExecutionEvidence:
        ev = ExecutionEvidence(
            transaction_id=transaction_id,
            target_root=str(self.target_root),
            candidate=candidate,
            workflow_hash=workflow_hash,
            policy_hash=policy_hash,
            approval_hash=approval_hash,
            boundary_hash=boundary_hash
        )
        self.save(ev)
        return ev
        
    def save(self, evidence: ExecutionEvidence):
        path = self.evidence_dir / f"{evidence.transaction_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(evidence.__dict__, indent=2))

    def finalize(self, evidence: ExecutionEvidence, final_status: str):
        evidence.final_status = final_status
        evidence.completed_at = time.time()
        evidence.evidence_hash = evidence.generate_hash()
        evidence.status = "COMPLETE"
        self.save(evidence)

    def load_and_verify(self, transaction_id: str) -> ExecutionEvidence:
        path = self.evidence_dir / f"{transaction_id}.json"
        if not path.exists():
            raise ValueError("Evidence not found")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
            
        ev = ExecutionEvidence(**data)
        if ev.status == "COMPLETE":
            expected_hash = ev.generate_hash()
            if ev.evidence_hash != expected_hash:
                ev.status = "INVALID"
        return ev
