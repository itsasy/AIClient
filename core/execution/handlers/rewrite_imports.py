from core.execution.operation_registry import OperationHandler
from core.execution.operations import OperationContract
from core.execution.handlers.base import ImmutableOperationContext, get_file_hash

class RewriteDeclaredImportsHandler(OperationHandler):
    def validate(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        src = context.target_root / contract.source
        if not src.exists():
            return "SOURCE_NOT_FOUND"
        if contract.source not in contract.boundary:
            return "BOUNDARY_VIOLATION"
        if contract.expected_hash and get_file_hash(src) != contract.expected_hash:
            return "CONCURRENT_MODIFICATION"
        res = sandbox.authorize_operation(contract.required_capability, contract.operation_type, [contract.source], [])
        if res != "READY": return res
        return "READY"

    def execute(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        src = context.target_root / contract.source
        content = src.read_text(encoding='utf-8')
        for k, v in contract.inputs.get("replacements", {}).items():
            content = content.replace(k, v)
        src.write_text(content, encoding='utf-8')
        return "SUCCESS"

    def observe(self, contract: OperationContract, context: ImmutableOperationContext) -> dict:
        src = context.target_root / contract.source
        return {"source_exists": src.exists(), "source_hash": get_file_hash(src)}
