import time
import uuid
import hashlib
import json
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path

@dataclass
class SessionEvent:
    event_id: str
    session_id: str
    transaction_id: str
    timestamp: float
    actor: str
    event_type: str
    payload_hash: str
    previous_hash: str
    event_hash: str = ""

    def calculate_hash(self) -> str:
        payload = f"{self.event_id}:{self.session_id}:{self.transaction_id}:{self.timestamp}:{self.actor}:{self.event_type}:{self.payload_hash}:{self.previous_hash}"
        return hashlib.sha256(payload.encode()).hexdigest()

class SessionJournal:
    def __init__(self, target_root: Path):
        self.target_root = Path(target_root)
        self.journal_dir = self.target_root / ".aiclient_journals"
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.events: Dict[str, List[SessionEvent]] = {}
        
    def _get_path(self, session_id: str) -> Path:
        return self.journal_dir / f"{session_id}.jsonl"

    def record(self, session_id: str, transaction_id: str, event_type: str, actor: str, payload: dict) -> SessionEvent:
        events = self.load(session_id, verify=False)
        previous_hash = events[-1].event_hash if events else "GENESIS"
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        
        event = SessionEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            transaction_id=transaction_id,
            timestamp=time.time(),
            actor=actor,
            event_type=event_type,
            payload_hash=payload_hash,
            previous_hash=previous_hash
        )
        event.event_hash = event.calculate_hash()
        
        path = self._get_path(session_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.__dict__) + "\n")
            
        if session_id not in self.events:
            self.events[session_id] = []
        self.events[session_id].append(event)
        
        return event

    def load(self, session_id: str, verify: bool = True) -> List[SessionEvent]:
        path = self._get_path(session_id)
        events = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    events.append(SessionEvent(**data))
                    
        if verify and events:
            for i, ev in enumerate(events):
                if ev.event_hash != ev.calculate_hash():
                    raise ValueError(f"JOURNAL_INTEGRITY_FAILED: event_hash tampered at {ev.event_id}")
                if i > 0 and ev.previous_hash != events[i-1].event_hash:
                    raise ValueError(f"JOURNAL_INTEGRITY_FAILED: previous_hash broken at {ev.event_id}")
                if i == 0 and ev.previous_hash != "GENESIS":
                    raise ValueError(f"JOURNAL_INTEGRITY_FAILED: genesis broken at {ev.event_id}")
                    
        return events
