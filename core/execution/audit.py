import time
import uuid
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    transaction_id: str
    timestamp: float
    candidate: str
    actor: str  # system, llm, human, skill, orchestrator, recovery
    status: str
    metadata: Dict[str, Any]

class AuditTrail:
    def __init__(self, target_root: Path):
        self.target_root = Path(target_root)
        self.audit_dir = self.target_root / ".aiclient_audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
    def _sanitize_metadata(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        safe = {}
        for k, v in meta.items():
            if any(secret in k.lower() for secret in ["password", "key", "token", "secret", "credentials"]):
                safe[k] = "[REDACTED]"
            elif isinstance(v, str) and any(secret in v.lower() for secret in [".env", "password=", "key="]):
                safe[k] = "[REDACTED]"
            else:
                safe[k] = v
        return safe

    def record(self, event_type: str, transaction_id: str, candidate: str, actor: str, status: str, metadata: Dict[str, Any] = None):
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            transaction_id=transaction_id,
            timestamp=time.time(),
            candidate=candidate,
            actor=actor,
            status=status,
            metadata=self._sanitize_metadata(metadata or {})
        )
        
        file_path = self.audit_dir / f"{transaction_id}_events.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.__dict__) + "\n")
            
        return event

    def query(self, transaction_id: Optional[str] = None, candidate: Optional[str] = None) -> List[AuditEvent]:
        results = []
        for file_path in self.audit_dir.glob("*_events.jsonl"):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    if transaction_id and data["transaction_id"] != transaction_id:
                        continue
                    if candidate and data["candidate"] != candidate:
                        continue
                    results.append(AuditEvent(**data))
        return sorted(results, key=lambda x: x.timestamp)
        
    def generate_report(self, transaction_id: str) -> str:
        events = self.query(transaction_id=transaction_id)
        if not events:
            return "No audit trail found."
            
        report = [f"Transformation Audit Report\nTransaction: {transaction_id}\n"]
        for e in events:
            report.append(f"[{e.timestamp}] {e.event_type} | Actor: {e.actor} | Status: {e.status}")
        return "\n".join(report)
