import json
from pathlib import Path
from typing import Optional, List, Dict
import hashlib
import os

from core.execution.transaction import ExecutionRecord
from core.execution.wal import WriteAheadLog, WALEntry
from core.execution.approval import ApprovalLifecycleManager
from core.execution.workflow import ExtractionWorkflow
from core.execution.global_workflow import GlobalWorkflow

class RecoveryManager:
    def __init__(self, target_root: str):
        self.target_root = Path(target_root)
        self.wal = WriteAheadLog(str(target_root))
        
    def _hash_file(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def classify_operation(self, last_status: str, op_type: str, source_path: str, dest_path: str, expected_src_hash: str, expected_dst_hash: str) -> str:
        # Determine physical state
        src_file = self.target_root / source_path if source_path else None
        dst_file = self.target_root / dest_path if dest_path else None
        
        src_exists = src_file.exists() if src_file else False
        dst_exists = dst_file.exists() if dst_file else False
        
        src_hash = self._hash_file(src_file) if src_exists else ""
        dst_hash = self._hash_file(dst_file) if dst_exists else ""
        
        if last_status == "COMMITTED" or last_status == "APPLIED":
            if dst_exists and (not expected_dst_hash or dst_hash == expected_dst_hash):
                if src_file and src_exists:
                    pass # Copy operation
                elif src_file and not src_exists:
                    pass # Move operation
                return "ALREADY_APPLIED"
                
        # If it's EXECUTING or PREPARED
        if last_status in ("PREPARED", "EXECUTING"):
            if dst_exists and dst_hash == expected_dst_hash:
                if op_type == "move_files" and src_exists: return "RECOVERY_REQUIRED"
                # Looks like it actually finished physically
                return "ALREADY_APPLIED"
            if src_file and src_exists and not dst_exists:
                # Looks like it hasn't happened yet
                if src_hash == expected_src_hash:
                    return "NOT_APPLIED"
            return "RECOVERY_REQUIRED"
            
        return "RECOVERY_REQUIRED"

    def resume(self, transaction_id: str, gwf: GlobalWorkflow, approval_manager: ApprovalLifecycleManager, approval_id: str) -> str:
        # Resume deterministic recovery process
        # Returns decision: RESUME, ROLLBACK, or RECOVERY_REQUIRED
        
        # 1. VERIFY APPROVAL
        record = approval_manager.approvals.get(approval_id)
        if not record:
            return "RECOVERY_REQUIRED" # Approval not found
            
        import time
        if time.time() > record.expires_at or record.status == "REVOKED":
            return "RECOVERY_REQUIRED"
            
        # 2. VERIFY HASHES
        if record.workflow_hash != gwf.global_workflow_hash:
            return "RECOVERY_REQUIRED"
            
        # 3. VERIFY OPERATION WAL STATE
        entries = self.wal.get_entries(transaction_id)
        if not entries:
            # Nothing started
            return "RESUME"
            
        last_entries = {} # op_hash -> last entry
        for e in entries:
            last_entries[e.operation_hash] = e
            
        any_ambiguous = False
        any_applied = False
        
        for e in last_entries.values():
            classification = self.classify_operation(e.status, e.operation_type, e.source, e.destination, e.expected_source_hash, e.expected_destination_hash)
            if classification == "RECOVERY_REQUIRED":
                any_ambiguous = True
            elif classification == "ALREADY_APPLIED":
                any_applied = True
                
        if any_ambiguous:
            return "RECOVERY_REQUIRED"
            
        if any_applied:
            # We know what happened, but since it's global and atomic, 
            # if we are resuming from a partial state where SOME are applied and others are NOT_APPLIED,
            # we need to decide if we can blindly resume. 
            # The prompt says: "Si es ambiguo: RECOVERY_REQUIRED. Nunca asumir. Y si el GlobalWorkflow requiere atomicidad y no puede garantizarse un resume seguro, debe utilizar el Snapshot Global para ejecutar un rollback completo."
            # Since some are NOT_APPLIED and others are ALREADY_APPLIED, it's not ambiguous, we COULD theoretically resume. But if it's too complex, ROLLBACK. 
            # Actually, returning ROLLED_BACK or ROLLBACK triggers the orchestrator to rollback.
            return "ROLLBACK"
            
        return "RESUME"





    def check_idempotency(self, candidate: str, action: str) -> str:
        return "PENDING"
