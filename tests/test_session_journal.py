import pytest
from core.execution.session_journal import SessionJournal

def test_session_journal_tamper_detection(tmp_path):
    journal = SessionJournal(tmp_path)
    journal.record("sess1", "tx1", "SESSION_CREATED", "system", {"k": "v"})
    journal.record("sess1", "tx1", "APPROVED", "human", {})
    
    events = journal.load("sess1", verify=True)
    assert len(events) == 2
    
    # Tamper with the JSON file directly
    import json
    path = tmp_path / ".aiclient_journals" / "sess1.jsonl"
    lines = path.read_text().splitlines()
    data = json.loads(lines[0])
    data["actor"] = "hacker"
    lines[0] = json.dumps(data)
    path.write_text("\n".join(lines) + "\n")
    
    with pytest.raises(ValueError, match="JOURNAL_INTEGRITY_FAILED"):
        journal.load("sess1", verify=True)
