import pytest
import time
from core.execution.approval import ApprovalLifecycleManager
from core.execution.session import SessionManager
from core.execution.workflow import ExtractionWorkflow, ExtractionWorkflowPlanner

class MockWorkflow:
    def __init__(self, wh):
        self.workflow_hash = wh

def test_execution_session_lifecycle(tmp_path):
    app_mgr = ApprovalLifecycleManager()
    sess_mgr = SessionManager(tmp_path, app_mgr)
    
    wf = MockWorkflow("whash1")
    sess = sess_mgr.create_session("auth", "task", wf, "phash", "bhash", 3600)
    assert sess.status == "CREATED"
    
    sess_mgr.generate_preview(sess.session_id, {"some": "data"})
    assert sess.status == "PREVIEWED"
    
    sess_mgr.request_approval(sess.session_id, ["move_files"])
    assert sess.status == "AWAITING_APPROVAL"
    
    sess_mgr.process_approval(sess.session_id, approved=True, actor="human")
    assert sess.status == "APPROVED"
    
    # Authorization Gate
    res = sess_mgr.authorize_execution(sess.session_id)
    assert res == "READY_TO_EXECUTE"
    assert sess.status == "READY_TO_EXECUTE"
    
    sess_mgr.mark_started(sess.session_id)
    assert sess.status == "EXECUTING"
    
    sess_mgr.mark_completed(sess.session_id, "COMMITTED")
    assert sess.status == "COMMITTED"

def test_session_authorization_expired(tmp_path):
    app_mgr = ApprovalLifecycleManager()
    sess_mgr = SessionManager(tmp_path, app_mgr)
    
    wf = MockWorkflow("whash2")
    sess = sess_mgr.create_session("auth", "task", wf, "phash", "bhash", -1) # Expired TTL
    sess_mgr.generate_preview(sess.session_id, {"some": "data"})
    sess_mgr.request_approval(sess.session_id, ["move_files"])
    sess_mgr.process_approval(sess.session_id, approved=True, actor="human")
    
    res = sess_mgr.authorize_execution(sess.session_id)
    assert res == "REJECTED: EXPIRED"

def test_session_authorization_already_finalized(tmp_path):
    app_mgr = ApprovalLifecycleManager()
    sess_mgr = SessionManager(tmp_path, app_mgr)
    wf = MockWorkflow("whash3")
    sess = sess_mgr.create_session("auth", "task", wf, "phash", "bhash", 3600)
    sess_mgr.generate_preview(sess.session_id, {"some": "data"})
    sess_mgr.request_approval(sess.session_id, ["move_files"])
    sess_mgr.process_approval(sess.session_id, approved=True, actor="human")
    
    sess_mgr.mark_completed(sess.session_id, "COMMITTED")
    
    res = sess_mgr.authorize_execution(sess.session_id)
    assert res == "SESSION_ALREADY_FINALIZED"
