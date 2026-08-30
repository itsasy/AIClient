import hashlib
from pathlib import Path
from core.execution.operation_registry import OperationHandler
from core.execution.operations import OperationContract

def get_file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()

class ImmutableOperationContext:
    def __init__(self, tx_id, session_id, wf_hash, policy_hash, app_hash, boundary_hash, skill_hash, cap_hash, sb_hash, target_root, proposal_hash="", specification_hash="", graph_hash=""):
        self.transaction_id = tx_id
        self.session_id = session_id
        self.workflow_hash = wf_hash
        self.policy_hash = policy_hash
        self.approval_hash = app_hash
        self.boundary_hash = boundary_hash
        self.skill_hash = skill_hash
        self.capability_hash = cap_hash
        self.sandbox_hash = sb_hash
        self.proposal_hash = proposal_hash
        self.specification_hash = specification_hash
        self.graph_hash = graph_hash
        self.target_root = Path(target_root)
        self.operation_hash = ""

    def validate_context(self, current_wf_hash, current_skill_hash):
        if self.workflow_hash != current_wf_hash:
            raise ValueError("EXECUTION_CONTEXT_MISMATCH")
        if self.skill_hash != current_skill_hash:
            raise ValueError("EXECUTION_CONTEXT_MISMATCH")

