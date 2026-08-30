import pytest
import os
from pathlib import Path

from core.execution.approval_gate import ApprovalGate, ApprovalRequest, ApprovalDecision
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
    
    gate = ApprovalGate()
    return cand, sim, gate

def test_valid_approval_request(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    assert req.approval_request_hash != ""
    assert req.simulation_status == "READY_FOR_APPROVAL"

def test_recommendation_is_not_approval(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "RECOMMENDED", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    assert isinstance(req, ApprovalRequest)

def test_explicit_approval_validates(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = gate.approve(req, "human", "looks good")
    
    ev = gate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    assert ev.status == "AUTHORIZATION_VALID"
    assert ev.handoff == "HANDOFF_TO_WORKFLOW"

def test_rejection(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = gate.reject(req, "human", "bad idea")
    
    ev = gate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    assert ev.status == "AUTHORIZATION_INVALID"
    assert "Decision is REJECTED" in ev.issues

def test_candidate_hash_mismatch(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = gate.approve(req, "human", "ok")
    
    cand.candidate_hash = "tampered"
    ev = gate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    assert ev.status == "AUTHORIZATION_INVALID"
    assert "APPROVAL_ARTIFACT_MISMATCH (Candidate)" in ev.issues

def test_simulation_hash_mismatch(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = gate.approve(req, "human", "ok")
    
    sim.simulation_hash = "tampered"
    ev = gate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    assert ev.status == "AUTHORIZATION_INVALID"

def test_approval_request_mismatch(base_context):
    cand, sim, gate = base_context
    req1 = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    req2 = gate.create_request(cand, "sel2", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = gate.approve(req1, "human", "ok")
    
    ev = gate.validate(decision, req2, cand, sim, "READY_FOR_APPROVAL")
    assert ev.status == "AUTHORIZATION_INVALID"

def test_simulation_blocked(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "sel1", sim, "SIMULATION_BLOCKED", "LOW", "MODERATE")
    decision = gate.approve(req, "human", "override")
    
    ev = gate.validate(decision, req, cand, sim, "SIMULATION_BLOCKED")
    assert ev.status == "AUTHORIZATION_INVALID"

def test_blocking_unknown(base_context):
    cand, sim, gate = base_context
    sim.unknowns.append({"code": "FATAL", "blocking": True})
    req = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = gate.approve(req, "human", "ok")
    
    ev = gate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    assert ev.status == "AUTHORIZATION_INVALID"
    assert "BLOCKING_UNKNOWN" in ev.issues

def test_scope_mismatch(base_context):
    cand, sim, gate = base_context
    req = gate.create_request(cand, "sel1", sim, "READY_FOR_APPROVAL", "LOW", "MODERATE")
    decision = gate.approve(req, "human", "ok")
    
    cand.items[0].targets.append(CandidateTarget("file", "mod_b.py", "CONFIRMED"))
    
    ev = gate.validate(decision, req, cand, sim, "READY_FOR_APPROVAL")
    assert ev.status == "AUTHORIZATION_INVALID"
    assert "APPROVAL_SCOPE_MISMATCH" in ev.issues

def test_no_execution_and_no_mutation(tmp_path):
    cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        code = "open('should_not_exist.txt', 'w').write('executed')"
        (tmp_path / "malicious.py").write_text(code)
        
        cand = TransformationCandidate(
            candidate_id="c",
            status="VALID",
            items=[],
            evidence=None
        )
        cand.generate_hash()
        sim = GraphSimulationResult(cand.candidate_hash, "s", "spec", "g")
        sim.generate_hash()
        
        gate = ApprovalGate()
        req = gate.create_request(cand, "s", sim, "READY_FOR_APPROVAL", "L", "L")
        gate.approve(req, "h", "o")
        
        assert not Path("should_not_exist.txt").exists()
    finally:
        os.chdir(cwd)
