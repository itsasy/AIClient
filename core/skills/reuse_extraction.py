from typing import Dict, List, Optional
from core.discovery.transformation import CandidateTransformationPlan, TransformationPlan
from core.discovery.transformation_policy import TransformationPolicy
from core.skills.registry import SkillRegistry
from core.execution.orchestrator import TransformationOrchestrator
from core.execution.transaction import ExecutionRecord
from core.execution.workflow import ExtractionWorkflow
from core.execution.approval import ApprovalRecord, ApprovalLifecycleManager
from core.execution.session import SessionManager, ExecutionSession

class ReuseExtractionSkill:
    def __init__(
        self,
        orchestrator: TransformationOrchestrator,
        policy: TransformationPolicy,
        registry: SkillRegistry,
        approvals: Dict[str, List[str]],
        session_mgr: Optional[SessionManager] = None
    ):
        self.orchestrator = orchestrator
        self.policy = policy
        self.registry = registry
        self.approvals = approvals
        self.session_mgr = session_mgr
        self.name = "reuse_extraction"
        self.version = "1.0"
        
    def preflight(self, workflow: ExtractionWorkflow, approval: Optional[ApprovalRecord], session: Optional[ExecutionSession] = None) -> str:
        if workflow.status == "BLOCKED":
            return f"REJECTED: {workflow.reason}"
            
        cand_policy = next((p for p in self.policy.decisions if p.candidate == workflow.candidate), None)
        if not cand_policy:
            return "REJECTED: No policy for candidate"
            
        if cand_policy.decision == "DENY":
            return "REJECTED: Policy DENY"
            
        supported_operations = [
            "inspect", "copy", "move", "rename", "rewrite_declared_import", 
            "create_declared_adapter", "move_files", "rewrite_imports", "copy_files"
        ]
        
        for step in workflow.graph.get_ordered_steps():
            if step.operation not in supported_operations:
                return f"REJECTED: UNSUPPORTED_OPERATION: {step.operation}"
                
            match = self.registry.match_capabilities(workflow.candidate, [step.operation])
            if not match.compatible:
                return f"REJECTED: Missing capability {step.operation}"

            for key, path_str in step.inputs.items():
                if path_str:
                    if "../" in str(path_str):
                        return "REJECTED: Path traversal"
                    if "secret" in str(path_str) or ".env" in str(path_str) or "credentials" in str(path_str):
                        return "REJECTED: Secret bearing file"

        if approval and approval.workflow_hash != workflow.workflow_hash:
            return "REJECTED: approval_mismatch"
            
        if session:
            if session.workflow_hash != workflow.workflow_hash:
                return "REJECTED: SESSION_MISMATCH"
                    
        return "READY"

    def execute(self, workflow: ExtractionWorkflow, approval: Optional[ApprovalRecord], approval_mgr: Optional[ApprovalLifecycleManager] = None, mode: str = "EXECUTE", session_id: Optional[str] = None) -> ExecutionRecord:
        
        session = None
        if self.session_mgr and session_id:
            session = self.session_mgr.sessions.get(session_id)
            if mode == "EXECUTE":
                auth_res = self.session_mgr.authorize_execution(session_id)
                if auth_res != "READY_TO_EXECUTE":
                    return self.orchestrator._create_rejection_evidence(workflow.candidate, auth_res, workflow, mode)
                self.session_mgr.mark_started(session_id)

        preflight_result = self.preflight(workflow, approval, session)
        if preflight_result.startswith("REJECTED"):
            if session:
                self.session_mgr.mark_completed(session_id, "REJECTED")
            return self.orchestrator._create_rejection_evidence(workflow.candidate, preflight_result, workflow, mode)
            
        # P14: The Orchestrator does the physical work, but the skill was authorized to call it.
        # Ensure we pass the same transaction_id if we have a session.
        tx_id_override = session.transaction_id if session else None
        
        record = self.orchestrator.execute_workflow(workflow, approval, approval_mgr, mode=mode, transaction_id=tx_id_override)
        
        if session:
            self.session_mgr.mark_completed(session_id, record.status)
            
        return record
