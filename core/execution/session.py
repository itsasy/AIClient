import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from pathlib import Path

from core.execution.workflow import ExtractionWorkflow
from core.execution.approval import ApprovalLifecycleManager, ApprovalRecord
from core.execution.session_journal import SessionJournal

@dataclass
class ExecutionSession:
    session_id: str
    transaction_id: str
    target_root: str
    candidate: str
    task: str
    
    workflow_hash: str
    policy_hash: str
    boundary_hash: str
    
    simulation_hash: str = ""
    selection_hash: str = ""
    registry_snapshot_hash: str = ""
    proposal_hash: str = ""
    specification_hash: str = ""
    selected_skill_ids: List[str] = field(default_factory=list)
    
    approval_id: Optional[str] = None
    preview_hash: str = ""
    
    mode: str = "EXECUTE"
    status: str = "CREATED"
    
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    expires_at: Optional[float] = None

class SessionManager:
    def __init__(self, target_root: Path, approval_mgr: ApprovalLifecycleManager):
        self.target_root = Path(target_root)
        self.approval_mgr = approval_mgr
        self.journal = SessionJournal(self.target_root)
        self.sessions: Dict[str, ExecutionSession] = {}

    def create_session(self, candidate: str, task: str, workflow: ExtractionWorkflow, policy_hash: str, boundary_hash: str, ttl: int = 3600) -> ExecutionSession:
        session_id = f"sess_{uuid.uuid4()}"
        transaction_id = f"tx_{uuid.uuid4()}"
        
        sess = ExecutionSession(
            session_id=session_id,
            transaction_id=transaction_id,
            target_root=str(self.target_root),
            candidate=candidate,
            task=task,
            workflow_hash=workflow.workflow_hash,
            policy_hash=policy_hash,
            boundary_hash=boundary_hash,
            expires_at=time.time() + ttl
        )
        self.sessions[session_id] = sess
        self.journal.record(session_id, transaction_id, "SESSION_CREATED", "system", {"ttl": ttl})
        return sess

    def generate_preview(self, session_id: str, preview_data: dict):
        sess = self.sessions[session_id]
        if sess.status != "CREATED":
            raise ValueError("Invalid state for PREVIEWED")
            
        sess.preview_hash = hashlib.sha256(str(preview_data).encode()).hexdigest()
        sess.status = "PREVIEWED"
        self.journal.record(session_id, sess.transaction_id, "PREVIEW_GENERATED", "system", {"preview_hash": sess.preview_hash})

    def request_approval(self, session_id: str, actions: list, simulation_hash: str = "", selection_hash: str = "", registry_snapshot_hash: str = "", proposal_hash: str = "", specification_hash: str = ""):
        sess = self.sessions[session_id]
        if sess.status != "PREVIEWED":
            raise ValueError("Invalid state for AWAITING_APPROVAL")
            
        sess.simulation_hash = simulation_hash
        sess.selection_hash = selection_hash
        sess.registry_snapshot_hash = registry_snapshot_hash
        sess.proposal_hash = proposal_hash
        sess.specification_hash = specification_hash
            
        approval = self.approval_mgr.request_approval(
            sess.transaction_id, sess.candidate, sess.workflow_hash, 
            sess.policy_hash, sess.boundary_hash, actions, 
            ttl=int(sess.expires_at - time.time()),
            simulation_hash=simulation_hash,
            selection_hash=selection_hash,
            registry_snapshot_hash=registry_snapshot_hash,
            proposal_hash=proposal_hash,
            specification_hash=specification_hash
        )
        sess.approval_id = approval.approval_id
        sess.status = "AWAITING_APPROVAL"
        self.journal.record(session_id, sess.transaction_id, "APPROVAL_REQUESTED", "system", {"approval_id": sess.approval_id})

    def process_approval(self, session_id: str, approved: bool, actor: str = "human"):
        sess = self.sessions[session_id]
        if sess.status != "AWAITING_APPROVAL":
            raise ValueError("Invalid state")
            
        if approved:
            self.approval_mgr.approve(sess.approval_id, actor)
            sess.status = "APPROVED"
            sess.approved_at = time.time()
            self.journal.record(session_id, sess.transaction_id, "APPROVED", actor, {})
        else:
            self.approval_mgr.revoke(sess.approval_id, actor)
            sess.status = "REJECTED"
            self.journal.record(session_id, sess.transaction_id, "REJECTED", actor, {})

    def authorize_execution(self, session_id: str) -> str:
        sess = self.sessions[session_id]
        
        try:
            self.journal.load(session_id, verify=True)
        except ValueError as e:
            sess.status = "RECOVERY_REQUIRED"
            return str(e)

        if sess.status in ("COMMITTED", "ROLLED_BACK", "REJECTED", "FAILED", "EXPIRED", "REVOKED"):
            return "SESSION_ALREADY_FINALIZED"
            
        if sess.status != "APPROVED":
            return f"REJECTED: Invalid session status {sess.status}"
            
        if time.time() > sess.expires_at:
            sess.status = "EXPIRED"
            self.journal.record(session_id, sess.transaction_id, "SESSION_EXPIRED", "system", {})
            return "REJECTED: EXPIRED"
            
        app_record = self.approval_mgr.approvals.get(sess.approval_id)
        if not app_record:
            return "REJECTED: missing_approval"
            
        if app_record.status != "APPROVED":
            return f"REJECTED: approval status is {app_record.status}"
            
        if app_record.workflow_hash != sess.workflow_hash or app_record.policy_hash != sess.policy_hash or app_record.boundary_hash != sess.boundary_hash:
            sess.status = "REJECTED"
            return "REJECTED: SESSION_MISMATCH"
            
        if app_record.selection_hash != sess.selection_hash or app_record.registry_snapshot_hash != sess.registry_snapshot_hash:
            sess.status = "REJECTED"
            return "REJECTED: EXECUTION_CONTEXT_MISMATCH"
            
        if app_record.proposal_hash != sess.proposal_hash:
            sess.status = "REJECTED"
            return "REJECTED: PROPOSAL_MISMATCH"
            
        if app_record.specification_hash != sess.specification_hash:
            sess.status = "REJECTED"
            return "REJECTED: SPECIFICATION_MISMATCH"
            
        sess.status = "READY_TO_EXECUTE"
        return "READY_TO_EXECUTE"

    def mark_started(self, session_id: str):
        sess = self.sessions[session_id]
        sess.status = "EXECUTING"
        sess.started_at = time.time()
        self.journal.record(session_id, sess.transaction_id, "EXECUTION_STARTED", "orchestrator", {})

    def mark_completed(self, session_id: str, final_status: str):
        sess = self.sessions[session_id]
        sess.status = final_status
        sess.completed_at = time.time()
        self.journal.record(session_id, sess.transaction_id, final_status, "orchestrator", {})
