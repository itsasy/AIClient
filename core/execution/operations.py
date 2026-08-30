import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class OperationContract:
    operation_type: str
    source: Optional[str] = None
    destination: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    required_capability: str = ""
    boundary: List[str] = field(default_factory=list)
    expected_hash: Optional[str] = None
    operation_hash: str = ""

    def calculate_hash(self) -> str:
        payload = {
            "type": self.operation_type,
            "source": self.source,
            "destination": self.destination,
            "inputs": self.inputs,
            "expected_hash": self.expected_hash,
            "required_capability": self.required_capability,
            "boundary": sorted(self.boundary)
        }
        self.operation_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.operation_hash

class MoveFilesContract(OperationContract):
    def __init__(self, source: str, destination: str, boundary: List[str], expected_hash: Optional[str] = None):
        super().__init__(
            operation_type="move_files",
            source=source,
            destination=destination,
            preconditions=["source_exists", "source_in_boundary", "destination_not_exists", "sandbox_allowed"],
            postconditions=["source_absent", "destination_exists", "destination_hash_matches"],
            required_capability="move_files",
            boundary=boundary,
            expected_hash=expected_hash
        )
        self.calculate_hash()

class CopyFilesContract(OperationContract):
    def __init__(self, source: str, destination: str, boundary: List[str], expected_hash: Optional[str] = None):
        super().__init__(
            operation_type="copy_files",
            source=source,
            destination=destination,
            preconditions=["source_exists", "destination_not_exists", "sandbox_allowed"],
            postconditions=["source_exists", "destination_exists", "destination_hash_matches", "source_hash_matches"],
            required_capability="copy_files",
            boundary=boundary,
            expected_hash=expected_hash
        )
        self.calculate_hash()

class RenameFilesContract(OperationContract):
    def __init__(self, source: str, destination: str, boundary: List[str], expected_hash: Optional[str] = None):
        super().__init__(
            operation_type="rename_files",
            source=source,
            destination=destination,
            preconditions=["source_exists", "destination_not_exists", "sandbox_allowed"],
            postconditions=["source_absent", "destination_exists", "destination_hash_matches"],
            required_capability="rename_files",
            boundary=boundary,
            expected_hash=expected_hash
        )
        self.calculate_hash()

class RewriteDeclaredImportsContract(OperationContract):
    def __init__(self, file_path: str, replacements: Dict[str, str], boundary: List[str], expected_hash: Optional[str] = None):
        super().__init__(
            operation_type="rewrite_declared_imports",
            source=file_path,
            inputs={"replacements": replacements},
            preconditions=["source_exists", "source_in_boundary", "sandbox_allowed"],
            postconditions=["source_exists", "source_hash_matches"],
            required_capability="rewrite_declared_imports",
            boundary=boundary,
            expected_hash=expected_hash
        )
        self.calculate_hash()

class CreateDeclaredAdapterContract(OperationContract):
    def __init__(self, destination: str, template: str, boundary: List[str], expected_hash: Optional[str] = None):
        super().__init__(
            operation_type="create_declared_adapter",
            destination=destination,
            inputs={"template": template},
            preconditions=["destination_not_exists", "sandbox_allowed"],
            postconditions=["destination_exists", "destination_hash_matches"],
            required_capability="create_declared_adapter",
            boundary=boundary,
            expected_hash=expected_hash
        )
        self.calculate_hash()
