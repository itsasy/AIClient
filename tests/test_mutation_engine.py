import pytest
from core.execution.mutation_engine import MutationEngine
from core.execution.operation_registry import OperationRegistry
from core.execution.handlers.base import ImmutableOperationContext
from core.execution.sandbox import ExecutionSandbox
from core.execution.handlers.move_files import MoveFilesHandler
from core.execution.operations import MoveFilesContract
import hashlib

def test_move_files_success(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hello")
    expected_hash = hashlib.sha256(b"hello").hexdigest()

    sandbox = ExecutionSandbox(tmp_path)
    registry = OperationRegistry()
    registry.register("move_files", MoveFilesHandler())
    engine = MutationEngine(registry, sandbox)

    contract = MoveFilesContract("a.txt", "b.txt", ["a.txt", "b.txt"], expected_hash=expected_hash)
    ctx = ImmutableOperationContext("tx", "sess", "wf", "pol", "app", "bound", "skill", "cap", "sb", tmp_path)
    ctx.allowed_operations = ["move_files"]

    res, obs = engine.execute_contract(contract, ctx, "EXECUTE")
    assert res == "SUCCESS"
    assert not src.exists()
    assert (tmp_path / "b.txt").exists()
    
def test_move_files_concurrent_mod(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hello world") # Different content!
    
    # Expected hash of "hello"
    expected_hash = hashlib.sha256(b"hello").hexdigest()

    sandbox = ExecutionSandbox(tmp_path)
    registry = OperationRegistry()
    registry.register("move_files", MoveFilesHandler())
    engine = MutationEngine(registry, sandbox)

    contract = MoveFilesContract("a.txt", "b.txt", ["a.txt", "b.txt"], expected_hash=expected_hash)
    ctx = ImmutableOperationContext("tx", "sess", "wf", "pol", "app", "bound", "skill", "cap", "sb", tmp_path)
    ctx.allowed_operations = ["move_files"]

    res, obs = engine.execute_contract(contract, ctx, "EXECUTE")
    assert res == "CONCURRENT_MODIFICATION"

def test_move_files_idempotent(tmp_path):
    dst = tmp_path / "b.txt"
    dst.write_text("hello")
    expected_hash = hashlib.sha256(b"hello").hexdigest()

    sandbox = ExecutionSandbox(tmp_path)
    registry = OperationRegistry()
    registry.register("move_files", MoveFilesHandler())
    engine = MutationEngine(registry, sandbox)

    contract = MoveFilesContract("a.txt", "b.txt", ["a.txt", "b.txt"], expected_hash=expected_hash)
    ctx = ImmutableOperationContext("tx", "sess", "wf", "pol", "app", "bound", "skill", "cap", "sb", tmp_path)
    ctx.allowed_operations = ["move_files"]

    # source missing, dst exists and matches hash -> ALREADY_APPLIED
    res, obs = engine.execute_contract(contract, ctx, "EXECUTE")
    assert res == "ALREADY_APPLIED"

def test_shell_unsupported(tmp_path):
    registry = OperationRegistry()
    with pytest.raises(ValueError, match="UNSUPPORTED_OPERATION"):
        registry.register("execute_shell", MoveFilesHandler())
