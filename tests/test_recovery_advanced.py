import pytest
import os
import shutil
from pathlib import Path
import time
import json
import uuid

from core.execution.wal import WriteAheadLog, WALEntry
from core.execution.recovery import RecoveryManager
from core.execution.transaction import ExecutionRecord
from core.execution.global_workflow import GlobalWorkflow
from core.execution.workflow import WorkflowGraph, ExtractionScope, ExtractionWorkflow, WorkflowStep
from core.execution.approval import ApprovalLifecycleManager

def test_recovery_ambiguous_state(tmp_path):
    rm = RecoveryManager(str(tmp_path))
    wal = WriteAheadLog(str(tmp_path))
    
    tx_id = str(uuid.uuid4())
    wf_hash = "mock_wf"
    
    # Simulate a crash during EXECUTING
    wal.append(WALEntry(tx_id, wf_hash, "op_1", 0, "move_files", "PREPARED", "source.py", "dest.py"))
    wal.append(WALEntry(tx_id, wf_hash, "op_1", 0, "move_files", "EXECUTING", "source.py", "dest.py", expected_destination_hash="5694d08a2e53ffcae0c3103e5ad6f6076abd960eb1f8a56577040bc1028f702b"))
    
    gwf = GlobalWorkflow("gwf_1", tx_id, global_workflow_hash=wf_hash)
    app_mgr = ApprovalLifecycleManager()
    approval = app_mgr.request_approval(tx_id, "GLOBAL", wf_hash, "p", "b", ["move_files"])
    app_mgr.approve(approval.approval_id)
    
    # Both files exist (source and dest), so it's partially applied (maybe midway through copy before delete)
    # This should be RECOVERY_REQUIRED because it expects either source only or dest only
    (tmp_path / "source.py").write_text("code")
    (tmp_path / "dest.py").write_text("code")
    
    res = rm.resume(tx_id, gwf, app_mgr, approval.approval_id)
    assert res == "RECOVERY_REQUIRED"

def test_recovery_applied_state(tmp_path):
    rm = RecoveryManager(str(tmp_path))
    wal = WriteAheadLog(str(tmp_path))
    
    tx_id = str(uuid.uuid4())
    wf_hash = "mock_wf"
    
    wal.append(WALEntry(tx_id, wf_hash, "op_1", 0, "move_files", "EXECUTING", "source.py", "dest.py", expected_destination_hash="5694d08a2e53ffcae0c3103e5ad6f6076abd960eb1f8a56577040bc1028f702b"))
    
    gwf = GlobalWorkflow("gwf_1", tx_id, global_workflow_hash=wf_hash)
    app_mgr = ApprovalLifecycleManager()
    approval = app_mgr.request_approval(tx_id, "GLOBAL", wf_hash, "p", "b", ["move_files"])
    app_mgr.approve(approval.approval_id)
    
    # Only dest exists, copy finished, delete finished
    (tmp_path / "dest.py").write_text("code")
    
    res = rm.resume(tx_id, gwf, app_mgr, approval.approval_id)
    # Since it's ALREADY_APPLIED but it's part of a global workflow, the naive resume returns ROLLBACK to force clean state
    assert res == "ROLLBACK"

def test_recovery_expired_approval(tmp_path):
    rm = RecoveryManager(str(tmp_path))
    wal = WriteAheadLog(str(tmp_path))
    
    tx_id = str(uuid.uuid4())
    wf_hash = "mock_wf"
    
    wal.append(WALEntry(tx_id, wf_hash, "op_1", 0, "move_files", "EXECUTING", "source.py", "dest.py", expected_destination_hash="5694d08a2e53ffcae0c3103e5ad6f6076abd960eb1f8a56577040bc1028f702b"))
    
    gwf = GlobalWorkflow("gwf_1", tx_id, global_workflow_hash=wf_hash)
    app_mgr = ApprovalLifecycleManager()
    approval = app_mgr.request_approval(tx_id, "GLOBAL", wf_hash, "p", "b", ["move_files"], ttl=-10) # Expired!
    app_mgr.approve(approval.approval_id)
    
    res = rm.resume(tx_id, gwf, app_mgr, approval.approval_id)
    assert res == "RECOVERY_REQUIRED"

