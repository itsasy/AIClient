from core.execution.operation_registry import OperationHandler
from core.execution.operations import OperationContract
from core.execution.handlers.base import ImmutableOperationContext, get_file_hash

class CreateDeclaredAdapterHandler(OperationHandler):
    def validate(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        dst = context.target_root / contract.destination
        if dst.exists():
            if contract.expected_hash and get_file_hash(dst) == contract.expected_hash:
                return "ALREADY_APPLIED"
            return "DESTINATION_CONFLICT"
        res = sandbox.authorize_operation(contract.required_capability, contract.operation_type, [], [contract.destination])
        if res != "READY": return res
        return "READY"

    def execute(self, contract: OperationContract, context: ImmutableOperationContext, sandbox) -> str:
        dst = context.target_root / contract.destination
        dst.parent.mkdir(parents=True, exist_ok=True)
        template = contract.inputs.get("template", "# Adapter placeholder\n")
        dst.write_text(template, encoding='utf-8')
        return "SUCCESS"

    def observe(self, contract: OperationContract, context: ImmutableOperationContext) -> dict:
        dst = context.target_root / contract.destination
        return {"destination_exists": dst.exists(), "destination_hash": get_file_hash(dst)}
