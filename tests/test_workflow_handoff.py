import pytest
import os
from pathlib import Path

from core.execution.workflow_handoff import (
    WorkflowHandoffGate, WorkflowHandoffRequest, WorkflowArtifactBinding,
    AuthorizedWorkflowContext, ExecutionReadyContract
)
from core.execution.approval_gate import ApprovalGate, ApprovalRequest, ApprovalDecision, AuthorizationEvidence
from core.execution.pre_approval_simulation import GraphSimulationResult, PredictedEffect
from core.execution.candidates import TransformationCandidate, CandidateItem, CandidateTarget, CandidateEvidence

@pytest.fixture
def base_context():
    cand = TransformationCandidate(
        candidate_id="cand1",
        status="VALID",
        items=[CandidateItem("item1", "MOVE", [CandidateTarget("file", "mod_a.py", "CONFIRMED")], ["move_files"])],
        evidence=CandidateEvidence("p", "s", "a", "sem")
    )
    cand.generate_hash()
    
    sim = GraphSimulationResult(
        candidate_hash=cand.candidate_hash,
        selection_hash="shash",
        specification_hash="spechash",
        graph_hash="ghash",
        predicted_effects=[PredictedEffect("mod_a.py", "move_files", "UNKNOWN", "MODIFIED_BY_MOVE_FILES", "ev", "INFERRED")],
        conflicts=[],
        unknowns=[]
    )
    sim.generate_hash()
    
    agate = ApprovalGate()
    req = agate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = agate.approve(req, "human", "looks good")
    evidence = agate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    
    hgate = WorkflowHandoffGate()
    return cand, sim, agate, req, decision, evidence, hgate

def test_valid_authorized_handoff(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision, "wf_1", "tx_1")
    
    assert handoff.workflow_handoff_hash != ""
    assert handoff.workflow_id == "wf_1"
    
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    assert val.status == "HANDOFF_VALID"
    
    contract = hgate.create_execution_ready_contract(handoff, val)
    assert contract.status == "READY_FOR_EXECUTION"
    assert contract.execution_ready_hash != ""

def test_rejected_approval(base_context):
    cand, sim, agate, req, _, _, hgate = base_context
    decision = agate.reject(req, "human", "bad")
    evidence = agate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    
    handoff = hgate.prepare_handoff(evidence, req, decision)
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    
    assert val.status == "HANDOFF_BLOCKED"
    assert any("AUTHORIZATION_INVALID" in i.code for i in val.issues)
    
    contract = hgate.create_execution_ready_contract(handoff, val)
    assert contract.status == "NOT_READY"

def test_candidate_hash_mismatch(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision)
    
    cand.candidate_hash = "tampered"
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    assert val.status == "HANDOFF_BLOCKED"
    assert any("ARTIFACT_HASH_MISMATCH" in i.code for i in val.issues)

def test_scope_mismatch(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision)
    
    handoff.scope.append("rogue_file.py")
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    assert val.status == "HANDOFF_BLOCKED"
    assert any("AUTHORIZED_SCOPE_MISMATCH" in i.code for i in val.issues)

def test_operation_mismatch(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision)
    
    handoff.required_operations.append("delete_files")
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    assert val.status == "HANDOFF_BLOCKED"
    assert any("AUTHORIZED_OPERATION_MISMATCH" in i.code for i in val.issues)

def test_risk_mismatch(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision)
    
    handoff.risk = "HIGH"
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    assert val.status == "HANDOFF_BLOCKED"
    assert any("AUTHORIZED_RISK_MISMATCH" in i.code for i in val.issues)

def test_predicted_effect_mismatch(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision)
    
    handoff.predicted_effects = [{"target": "mod_a.py", "operation": "move_files", "predicted_state": "MODIFIED_BY_DELETE"}]
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    assert val.status == "HANDOFF_BLOCKED"
    assert any("PREDICTED_EFFECT_MISMATCH" in i.code for i in val.issues)

def test_blocking_unknown(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision)
    
    handoff.unknowns.append({"code": "FATAL", "blocking": True})
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
    assert val.status == "HANDOFF_BLOCKED"
    assert any("BLOCKING_UNKNOWN" in i.code for i in val.issues)

def test_stale_authorization(base_context):
    cand, sim, agate, req, decision, evidence, hgate = base_context
    handoff = hgate.prepare_handoff(evidence, req, decision)
    
    sim2 = GraphSimulationResult(cand.candidate_hash, "new_shash", "s", "g")
    sim2.generate_hash()
    
    val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim2)
    assert val.status == "HANDOFF_BLOCKED"
    assert any("ARTIFACT_HASH_MISMATCH" in i.code for i in val.issues)

def test_no_execution_and_no_mutation(tmp_path):
    cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        code = "open('should_not_exist.txt', 'w').write('executed')"
        (tmp_path / "malicious.py").write_text(code)
        
        cand = TransformationCandidate(candidate_id="c", status="VALID", items=[], evidence=None)
        cand.generate_hash()
        sim = GraphSimulationResult(cand.candidate_hash, "s", "spec", "g")
        sim.generate_hash()
        agate = ApprovalGate()
        req = agate.create_request(cand, "s", sim, "READY_FOR_APPROVAL", "L", "L")
        decision = agate.approve(req, "h", "o")
        evidence = agate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
        
        hgate = WorkflowHandoffGate()
        handoff = hgate.prepare_handoff(evidence, req, decision)
        val = hgate.validate_handoff(handoff, evidence, req, decision, cand, sim)
        contract = hgate.create_execution_ready_contract(handoff, val)
        
        assert contract.status == "READY_FOR_EXECUTION"
        assert not Path("should_not_exist.txt").exists()
    finally:
        os.chdir(cwd)
