import pytest
from core.execution.audit import AuditTrail

def test_audit_recording(tmp_path):
    audit = AuditTrail(tmp_path)
    audit.record("approval_requested", "tx1", "auth", "human", "REQUESTED", {"k": "v"})
    audit.record("execution_started", "tx1", "auth", "orchestrator", "EXECUTING")
    
    events = audit.query("tx1")
    assert len(events) == 2
    assert events[0].event_type == "approval_requested"
    assert events[0].actor == "human"
    assert events[1].event_type == "execution_started"
    assert events[1].actor == "orchestrator"

def test_audit_no_secrets(tmp_path):
    audit = AuditTrail(tmp_path)
    audit.record("test_event", "tx2", "auth", "system", "SUCCESS", {
        "password": "supersecret",
        "normal": "value",
        "api_key": "12345"
    })
    
    events = audit.query("tx2")
    assert len(events) == 1
    meta = events[0].metadata
    assert meta["password"] == "[REDACTED]"
    assert meta["api_key"] == "[REDACTED]"
    assert meta["normal"] == "value"
