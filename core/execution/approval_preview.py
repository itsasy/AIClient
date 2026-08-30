from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from core.execution.workflow import ExtractionWorkflow
from core.discovery.transformation_policy import TransformationPolicy

@dataclass
class ApprovalRecord:
    approval_id: str
    transaction_id: str
    candidate: str
    workflow_hash: str
    approved_actions: List[str]
    approved_at: float
    expires_at: float
    scope: str = "workflow"

class ApprovalPreviewGenerator:
    def __init__(self, policy: TransformationPolicy):
        self.policy = policy

    def generate_preview(self, workflow: ExtractionWorkflow) -> Dict[str, Any]:
        if workflow.status == "BLOCKED":
            return {
                "candidate": workflow.candidate,
                "status": "BLOCKED",
                "reason": workflow.reason
            }
            
        cand_policy = next((p for p in self.policy.decisions if p.candidate == workflow.candidate), None)
        
        operations = []
        approval_required = []
        files_to_move = 0
        files_to_create = 0
        files_to_modify = 0
        adapters = []
        
        for step in workflow.graph.get_ordered_steps():
            operations.append(step.operation)
            if step.required_approval:
                approval_required.append(step.operation)
                
            op = step.operation
            if op in ("move_files", "rename_files"):
                files_to_move += 1
            elif op in ("copy_files"):
                files_to_create += 1
            elif op in ("rewrite_declared_imports", "rewrite_imports"):
                files_to_modify += 1
            elif op == "create_declared_adapter":
                files_to_create += 1
                adapters.append(step.inputs.get("destination"))
                
        verification = [p.type for p in cand_policy.postconditions] if cand_policy else []

        return {
            "candidate": workflow.candidate,
            "readiness": "READY",
            "policy": cand_policy.decision if cand_policy else "UNKNOWN",
            "operations": operations,
            "files_to_move": files_to_move,
            "files_to_create": files_to_create,
            "files_to_modify": files_to_modify,
            "adapters": adapters,
            "verification": verification,
            "rollback": True,
            "approval_required": approval_required,
            "workflow_hash": workflow.workflow_hash
        }
