from typing import Dict, Type
from core.execution.operations import OperationContract

class OperationHandler:
    def validate(self, contract: OperationContract, context, sandbox) -> str:
        raise NotImplementedError
        
    def execute(self, contract: OperationContract, context, sandbox) -> str:
        raise NotImplementedError
        
    def observe(self, contract: OperationContract, context) -> Dict[str, str]:
        raise NotImplementedError

class OperationRegistry:
    def __init__(self):
        self.handlers: Dict[str, OperationHandler] = {}
        
    def register(self, operation_type: str, handler: OperationHandler):
        if operation_type in self.handlers:
            raise ValueError("OPERATION_REGISTRATION_CONFLICT")
        if operation_type == "execute_shell":
            raise ValueError("UNSUPPORTED_OPERATION")
        self.handlers[operation_type] = handler
        
    def get_handler(self, operation_type: str) -> OperationHandler:
        if operation_type not in self.handlers:
            raise ValueError("UNREGISTERED_HANDLER")
        return self.handlers[operation_type]
