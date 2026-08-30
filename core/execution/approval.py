import time
import uuid
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

@dataclass
class ApprovalRecord:
    approval_id: str
    transaction_id: str
    candidate: str
    workflow_hash: str
    policy_hash: str
    boundary_hash: str
    simulation_hash: str
    selection_hash: str
    registry_snapshot_hash: str
    proposal_hash: str
    specification_hash: str
    approved_actions: List[str]
    created_at: float
    expires_at: float
    
    status: str = "REQUESTED" # REQUESTED, PREVIEWED, APPROVED, REJECTED, EXPIRED, REVOKED, CONSUMED
    actor: str = "human"
    
    @property
    def approval_hash(self) -> str:
        payload = f"{self.approval_id}:{self.workflow_hash}:{self.policy_hash}:{self.boundary_hash}:{self.simulation_hash}:{self.selection_hash}:{self.registry_snapshot_hash}:{self.proposal_hash}:{self.specification_hash}"
        return hashlib.sha256(payload.encode()).hexdigest()

class ApprovalLifecycleManager:
    def __init__(self):
        self.approvals: Dict[str, ApprovalRecord] = {}

    def request_approval(self, transaction_id: str, candidate: str, workflow_hash: str, policy_hash: str, boundary_hash: str, actions: List[str], ttl: int = 3600, simulation_hash: str = "", selection_hash: str = "", registry_snapshot_hash: str = "", proposal_hash: str = "", specification_hash: str = "") -> ApprovalRecord:
        record = ApprovalRecord(
            approval_id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            candidate=candidate,
            workflow_hash=workflow_hash,
            policy_hash=policy_hash,
            boundary_hash=boundary_hash,
            simulation_hash=simulation_hash,
            selection_hash=selection_hash,
            registry_snapshot_hash=registry_snapshot_hash,
            proposal_hash=proposal_hash,
            specification_hash=specification_hash,
            approved_actions=actions,
            created_at=time.time(),
            expires_at=time.time() + ttl,
            status="REQUESTED"
        )
        self.approvals[record.approval_id] = record
        return record

    def preview(self, approval_id: str):
        if self.approvals[approval_id].status == "REQUESTED":
            self.approvals[approval_id].status = "PREVIEWED"

    def approve(self, approval_id: str, actor: str = "human"):
        record = self.approvals.get(approval_id)
        if not record:
            raise ValueError("Approval not found")
        if record.status not in ("REQUESTED", "PREVIEWED"):
            raise ValueError(f"Cannot approve from status {record.status}")
        record.status = "APPROVED"
        record.actor = actor

    def revoke(self, approval_id: str, actor: str = "human"):
        record = self.approvals.get(approval_id)
        if record and record.status == "APPROVED":
            record.status = "REVOKED"

    def consume(self, approval_id: str, workflow_hash: str, simulation_hash: str = "", selection_hash: str = "", registry_snapshot_hash: str = "", proposal_hash: str = "", specification_hash: str = "") -> str:
        record = self.approvals.get(approval_id)
        if not record:
            return "REJECTED: approval_not_found"
            
        if time.time() > record.expires_at:
            record.status = "EXPIRED"
            return "REJECTED: APPROVAL_EXPIRED"
            
        if record.status == "REVOKED":
            return "REJECTED: APPROVAL_REVOKED"
            
        if record.status == "CONSUMED":
            return "REJECTED: REPLAY_REJECTED"
            
        if record.status != "APPROVED":
            return f"REJECTED: Invalid status {record.status}"
            
        if record.workflow_hash != workflow_hash:
            return "REJECTED: APPROVAL_MISMATCH"
            
        if simulation_hash and record.simulation_hash and record.simulation_hash != simulation_hash:
            return "REJECTED: APPROVAL_MISMATCH (SIMULATION)"
            
        if selection_hash and record.selection_hash and record.selection_hash != selection_hash:
            return "REJECTED: APPROVAL_MISMATCH (SELECTION)"
            
        if registry_snapshot_hash and record.registry_snapshot_hash and record.registry_snapshot_hash != registry_snapshot_hash:
            return "REJECTED: SKILL_REGISTRY_MISMATCH"
            
        if proposal_hash and record.proposal_hash and record.proposal_hash != proposal_hash:
            return "REJECTED: PROPOSAL_MISMATCH"
            
        if specification_hash and record.specification_hash and record.specification_hash != specification_hash:
            return "REJECTED: SPECIFICATION_MISMATCH"
            
        record.status = "CONSUMED"
        return "SUCCESS"
