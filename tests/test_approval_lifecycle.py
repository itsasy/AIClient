import pytest
import time
from core.execution.approval import ApprovalLifecycleManager

def test_approval_lifecycle():
    mgr = ApprovalLifecycleManager()
    
    # Caso A - Approval Exitoso
    app = mgr.request_approval("tx1", "auth", "whash", "phash", "bhash", ["move_files"], ttl=3600)
    assert app.status == "REQUESTED"
    
    mgr.preview(app.approval_id)
    assert mgr.approvals[app.approval_id].status == "PREVIEWED"
    
    mgr.approve(app.approval_id, "human")
    assert mgr.approvals[app.approval_id].status == "APPROVED"
    assert mgr.approvals[app.approval_id].actor == "human"
    
    # Consumir validamente
    res = mgr.consume(app.approval_id, "whash")
    assert res == "SUCCESS"
    assert mgr.approvals[app.approval_id].status == "CONSUMED"

def test_approval_revoke():
    mgr = ApprovalLifecycleManager()
    app = mgr.request_approval("tx2", "auth", "whash", "phash", "bhash", ["move_files"], ttl=3600)
    mgr.approve(app.approval_id)
    
    # Caso D - Revoked
    mgr.revoke(app.approval_id)
    assert mgr.approvals[app.approval_id].status == "REVOKED"
    
    res = mgr.consume(app.approval_id, "whash")
    assert res == "REJECTED: APPROVAL_REVOKED"

def test_approval_expired():
    mgr = ApprovalLifecycleManager()
    app = mgr.request_approval("tx3", "auth", "whash", "phash", "bhash", ["move_files"], ttl=-1)
    mgr.approve(app.approval_id)
    
    # Caso C - Expired
    res = mgr.consume(app.approval_id, "whash")
    assert res == "REJECTED: APPROVAL_EXPIRED"

def test_approval_mismatch():
    mgr = ApprovalLifecycleManager()
    app = mgr.request_approval("tx4", "auth", "whash", "phash", "bhash", ["move_files"], ttl=3600)
    mgr.approve(app.approval_id)
    
    # Caso B - Mismatch
    res = mgr.consume(app.approval_id, "whash_changed")
    assert res == "REJECTED: APPROVAL_MISMATCH"
