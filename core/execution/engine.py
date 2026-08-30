import shutil
import os
import uuid
from typing import Dict, List, Optional
from pathlib import Path

from core.execution.transaction import ExecutionRecord
from core.execution.rollback import RollbackManager
from core.execution.verification import VerificationEngine
from core.execution.manifest import ChangeManifest
from core.discovery.transformation import ExtractionAction

from core.execution.wal import WriteAheadLog
from core.execution.operations import MoveFilesContract, CopyFilesContract, RenameFilesContract, RewriteDeclaredImportsContract, CreateDeclaredAdapterContract
from core.execution.mutation_engine import MutationEngine
from core.execution.operation_registry import OperationRegistry
from core.execution.handlers.base import ImmutableOperationContext
from core.execution.handlers.move_files import MoveFilesHandler
from core.execution.handlers.copy_files import CopyFilesHandler
from core.execution.handlers.rewrite_imports import RewriteDeclaredImportsHandler
from core.execution.handlers.create_adapter import CreateDeclaredAdapterHandler
from core.execution.sandbox import ExecutionSandbox

class ExecutionEngine:
    def __init__(self, target_root, plan, policy, registry, approvals):
        self.target_root = Path(target_root)
        self.plan = plan
        self.policy = policy
        self.registry = registry
        self.approvals = approvals
        self.verification_engine = VerificationEngine(self.target_root)
        
        # P16: Initialize deterministic engine
        self.sandbox = ExecutionSandbox(self.target_root)
        self.operation_registry = OperationRegistry()
        self.operation_registry.register("move_files", MoveFilesHandler())
        self.operation_registry.register("copy_files", CopyFilesHandler())
        self.operation_registry.register("rewrite_declared_imports", RewriteDeclaredImportsHandler())
        self.operation_registry.register("rewrite_imports", RewriteDeclaredImportsHandler())
        self.operation_registry.register("create_declared_adapter", CreateDeclaredAdapterHandler())
        self.wal = WriteAheadLog(str(self.target_root))
        self.mutation_engine = MutationEngine(self.operation_registry, self.sandbox, self.wal)

    def execute(self, candidate: str, actions: List[ExtractionAction], mode: str = "EXECUTE", transaction_id: Optional[str] = None, skip_lock: bool = False, rollback_mgr=None) -> ExecutionRecord:
        transaction_id = transaction_id or str(uuid.uuid4())
        record = ExecutionRecord(transaction_id, str(self.target_root), candidate, mode=mode, status="PLANNED")
        
        cand_plan = next((p for p in self.plan.candidates if p.candidate == candidate), None)
        if not cand_plan:
            record.error = "Candidate not found in plan"
            record.status = "REJECTED"
            return record

        match = self.registry.match_capabilities(candidate, [a.operation for a in actions])
        if not match.compatible:
            record.error = f"CAPABILITY_MISSING"
            record.status = "REJECTED"
            return record
            
        registered_skill = self.registry.get_skill(match.matching_skill)

        if not rollback_mgr: rollback_mgr = RollbackManager(self.target_root, transaction_id)
        
        boundary = [str(f) for f in cand_plan.boundary.include]
        for act in actions:
            if act.source: boundary.append(str(act.source))
            if act.destination: boundary.append(str(act.destination))
        boundary = list(set(boundary))

        ctx = ImmutableOperationContext(
            tx_id=transaction_id,
            session_id="mock_session",
            wf_hash="mock_wf",
            policy_hash="mock_policy",
            app_hash="mock_app",
            boundary_hash="mock_boundary",
            skill_hash=registered_skill.identity.implementation_hash if registered_skill else "mock",
            cap_hash=registered_skill.attestation.attestation_hash if registered_skill else "mock",
            sb_hash="mock_sb",
            target_root=self.target_root
        )
        ctx.allowed_operations = registered_skill.attestation.capabilities if registered_skill else []

        if mode == "EXECUTE":
            record.status = "EXECUTING"
            if not skip_lock: rollback_mgr.snapshot(boundary)
            
            try:
                for act in actions:
                    contract = None
                    if act.operation == "move_files":
                        contract = MoveFilesContract(act.source, act.destination, boundary)
                    elif act.operation == "copy_files":
                        contract = CopyFilesContract(act.source, act.destination, boundary)
                    elif act.operation in ("rewrite_declared_imports", "rewrite_imports"):
                        contract = RewriteDeclaredImportsContract(act.source, {act.target: act.destination}, boundary)
                    elif act.operation == "create_declared_adapter":
                        contract = CreateDeclaredAdapterContract(act.destination, template="# Adapter placeholder\n", boundary=boundary)
                    else:
                        raise Exception(f"UNSUPPORTED_OPERATION: {act.operation}")
                        
                    res, obs = self.mutation_engine.execute_contract(contract, ctx, mode)
                    if res != "SUCCESS":
                        record.error = res
                        record.status = "ROLLED_BACK"
                        if not skip_lock: rollback_mgr.rollback()
                        return record
                    
                    if act.destination: 
                        record.files_changed.append(act.destination)
                        if act.operation in ("move_files", "copy_files", "create_declared_adapter"):
                            rollback_mgr.record_new_file(act.destination)
                    if act.source: 
                        record.files_changed.append(act.source)
                        
            except Exception as e:
                if not skip_lock: rollback_mgr.rollback()
                record.error = f"Execution failed: {str(e)}"
                record.status = "ROLLED_BACK"
                return record
                
            record.status = "COMMITTED"
            if not skip_lock: rollback_mgr.cleanup()
        else:
            record.status = "SUCCESS"

        record.files_changed = list(set(record.files_changed))
        return record




