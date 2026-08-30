import shutil
from core.execution.operation_registry import OperationHandler
from core.execution.operations import OperationContract
from core.execution.handlers.base import ImmutableOperationContext, get_file_hash

class CopyFilesHandler(OperationHandler):
    def validate(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        src = context.target_root / contract.source
        dst = context.target_root / contract.destination
        if not src.exists():
            if dst.exists(): return "ALREADY_APPLIED" if get_file_hash(dst) == contract.expected_hash else "CONFLICT"
            return "SOURCE_NOT_FOUND"
        if dst.exists(): return "DESTINATION_CONFLICT"
        res = sandbox.authorize_operation(contract.required_capability, contract.operation_type, [contract.source], [contract.destination])
        if res != "READY": return res
        return "READY"

    def execute(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        src = context.target_root / contract.source
        dst = context.target_root / contract.destination
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return "SUCCESS"

    def observe(self, contract: OperationContract, context: ImmutableOperationContext) -> dict:
        src = context.target_root / contract.source
        dst = context.target_root / contract.destination
        return {"source_exists": src.exists(), "destination_exists": dst.exists(), "destination_hash": get_file_hash(dst)}
