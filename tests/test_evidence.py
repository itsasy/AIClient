import pytest
from core.execution.evidence import EvidenceManager, ExecutionEvidence

def test_evidence_creation(tmp_path):
    mgr = EvidenceManager(tmp_path)
    ev = mgr.create("tx1", "auth", "whash", "phash", "ahash", "bhash")
    
    assert ev.status == "COLLECTING"
    assert (tmp_path / ".aiclient_evidence" / "tx1.json").exists()

def test_evidence_finalize(tmp_path):
    mgr = EvidenceManager(tmp_path)
    ev = mgr.create("tx2", "auth", "whash", "phash", "ahash", "bhash")
    mgr.finalize(ev, "COMMITTED")
    
    assert ev.status == "COMPLETE"
    assert ev.final_status == "COMMITTED"
    assert ev.evidence_hash != ""

def test_evidence_tamper_detection(tmp_path):
    mgr = EvidenceManager(tmp_path)
    ev = mgr.create("tx3", "auth", "whash", "phash", "ahash", "bhash")
    mgr.finalize(ev, "COMMITTED")
    
    # Tamper
    import json
    path = tmp_path / ".aiclient_evidence" / "tx3.json"
    data = json.loads(path.read_text())
    data["workflow_hash"] = "tampered"
    path.write_text(json.dumps(data))
    
    # Validate
    loaded = mgr.load_and_verify("tx3")
    assert loaded.status == "INVALID"
