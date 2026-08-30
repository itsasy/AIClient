import pytest
from pathlib import Path
from core.execution.sandbox import ExecutionSandbox

def test_execution_sandbox_valid(tmp_path):
    sandbox = ExecutionSandbox(tmp_path)
    # Testing valid move
    res = sandbox.authorize_operation("move_files", "move_files", ["modules/a.py"], ["shared/a.py"])
    assert res == "READY"

def test_execution_sandbox_shell_escalation(tmp_path):
    sandbox = ExecutionSandbox(tmp_path)
    # Shell escalation
    res = sandbox.authorize_operation("move_files", "subprocess", ["modules/a.py"], ["shared/a.py"])
    assert "REJECTED" in res
    assert "escalation" in res

def test_execution_sandbox_path_traversal(tmp_path):
    sandbox = ExecutionSandbox(tmp_path)
    res = sandbox.authorize_operation("move_files", "move_files", ["modules/a.py"], ["../../outside/a.py"])
    assert "REJECTED" in res

def test_execution_sandbox_secrets(tmp_path):
    sandbox = ExecutionSandbox(tmp_path)
    res = sandbox.authorize_operation("move_files", "move_files", [".env"], ["shared/.env"])
    assert "REJECTED" in res
