import pytest
from core.execution.approval import ApprovalLifecycleManager

def test_replay_protection():
    mgr = ApprovalLifecycleManager()
    app = mgr.request_approval("tx1", "auth", "whash", "phash", "bhash", ["move_files"], ttl=3600)
    mgr.approve(app.approval_id)
    
    # First consume
    res = mgr.consume(app.approval_id, "whash")
    assert res == "SUCCESS"
    assert mgr.approvals[app.approval_id].status == "CONSUMED"
    
    # Replay attempt
    res2 = mgr.consume(app.approval_id, "whash")
    assert res2 == "REJECTED: REPLAY_REJECTED"
