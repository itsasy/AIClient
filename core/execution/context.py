from dataclasses import dataclass
from typing import List
from pathlib import Path

@dataclass
class ImmutableExecutionContext:
    transaction_id: str
    session_id: str
    approval_id: str
    workflow_hash: str
    policy_hash: str
    boundary_hash: str
    skill_id: str
    skill_hash: str
    capability_hash: str
    target_root: str
    allowed_operations: List[str]

    def verify_integrity(self, current_workflow_hash: str, current_skill_hash: str):
        if self.workflow_hash != current_workflow_hash:
            raise ValueError("EXECUTION_CONTEXT_MISMATCH: workflow_hash changed")
        if self.skill_hash != current_skill_hash:
            raise ValueError("EXECUTION_CONTEXT_MISMATCH: skill_hash changed")
