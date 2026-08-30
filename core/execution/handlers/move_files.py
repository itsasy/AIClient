import shutil
from pathlib import Path
from core.execution.operation_registry import OperationHandler
from core.execution.operations import OperationContract
from core.execution.handlers.base import ImmutableOperationContext, get_file_hash

class MoveFilesHandler(OperationHandler):
    def validate(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        src = context.target_root / contract.source
        dst = context.target_root / contract.destination
        
        # Preconditions
        if not src.exists():
            # Check for idempotency
            if dst.exists():
                if contract.expected_hash and get_file_hash(dst) == contract.expected_hash:
                    return "ALREADY_APPLIED"
                return "CONFLICT"
            return "SOURCE_NOT_FOUND"
            
        if dst.exists():
            return "DESTINATION_CONFLICT"
            
        if contract.source not in contract.boundary:
            return "BOUNDARY_VIOLATION"
            
        # Concurrency protection
        if contract.expected_hash and get_file_hash(src) != contract.expected_hash:
            return "CONCURRENT_MODIFICATION"
            
        # Sandbox check
        res = sandbox.authorize_operation(contract.required_capability, contract.operation_type, [contract.source], [contract.destination])
        if res != "READY":
            return res
            
        return "READY"

    def execute(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        src = context.target_root / contract.source
        dst = context.target_root / contract.destination
        
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            return "SUCCESS"
        except Exception:
            return "OPERATION_INVALID"

    def observe(self, contract: OperationContract, context: ImmutableOperationContext) -> dict:
        src = context.target_root / contract.source
        dst = context.target_root / contract.destination
        return {
            "source_absent": not src.exists(),
            "destination_exists": dst.exists(),
            "destination_hash": get_file_hash(dst)
        }
