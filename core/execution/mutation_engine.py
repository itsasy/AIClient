from typing import List, Dict, Tuple
from core.execution.operations import OperationContract
from core.execution.operation_registry import OperationRegistry
from core.execution.handlers.base import ImmutableOperationContext
from core.execution.sandbox import ExecutionSandbox
from core.execution.wal import WriteAheadLog, WALEntry

class MutationEngine:
    def __init__(self, registry: OperationRegistry, sandbox: ExecutionSandbox, wal: WriteAheadLog = None):
        self.registry = registry
        self.sandbox = sandbox
        self.wal = wal

    def _write_wal(self, contract: OperationContract, context: ImmutableOperationContext, status: str):
        if not self.wal:
            return
        entry = WALEntry(
            transaction_id=context.transaction_id,
            workflow_hash=context.workflow_hash,
            proposal_hash=getattr(context, "proposal_hash", ""),
            specification_hash=getattr(context, "specification_hash", ""),
            graph_hash=getattr(context, "graph_hash", ""),
            operation_hash=context.operation_hash,
            operation_index=0,
            operation_type=contract.operation_type,
            status=status,
            source=contract.source,
            destination=contract.destination,
            expected_source_hash="", # Should derive from observation or pre-checks
            expected_destination_hash=""
        )
        self.wal.append(entry)

    def execute_contract(self, contract: OperationContract, context: ImmutableOperationContext, mode: str = "EXECUTE") -> Tuple[str, dict]:
        context.operation_hash = contract.calculate_hash()
        
        try:
            handler = self.registry.get_handler(contract.operation_type)
        except ValueError as e:
            return str(e), {}
            
        if contract.required_capability not in context.allowed_operations:
            return "CAPABILITY_MISSING", {}
            
        validation_res = handler.validate(contract, context, self.sandbox)
        if validation_res != "READY":
            return validation_res, {}

        if mode == "DRY_RUN":
            return "SUCCESS", {"dry_run": True}
            
        self._write_wal(contract, context, "PREPARED")
        self._write_wal(contract, context, "EXECUTING")
        
        exec_res = handler.execute(contract, context, self.sandbox)
        if exec_res != "SUCCESS":
            self._write_wal(contract, context, "FAILED")
            return exec_res, {}
            
        observation = handler.observe(contract, context)
        
        # Verify Postconditions
        for post in contract.postconditions:
            if post == "source_absent" and not observation.get("source_absent"):
                self._write_wal(contract, context, "UNKNOWN")
                return "OPERATION_VERIFICATION_FAILED", observation
            if post == "destination_exists" and not observation.get("destination_exists"):
                self._write_wal(contract, context, "UNKNOWN")
                return "OPERATION_VERIFICATION_FAILED", observation
                
        self._write_wal(contract, context, "APPLIED")
        return "SUCCESS", observation

