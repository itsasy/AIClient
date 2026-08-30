import pytest
from core.execution.proposal import TransformationProposal, Requirement, ProposalItem
from core.execution.specification import (
    TransformationSpecificationBuilder, TransformationSpecification, 
    TransformationSpecItem, TransformationTarget, TransformationDependency, Unknown, TransformationPrecondition
)

def test_case_a_valid_specification():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[Requirement("r1", "desc")],
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["move_files"])]
    )
    prop.generate_hash()
    
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec = builder.build_from_proposal(prop)
    assert spec.status == "VALID"
    assert spec.specification_hash != ""

def test_case_b_traceability_failure():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[], # Missing req
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["move_files"])]
    )
    prop.generate_hash()
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec = builder.build_from_proposal(prop)
    assert spec.status == "TRACEABILITY_FAILURE"

def test_case_c_boundary_conflict():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[Requirement("r1", "desc")],
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["move_files"])],
        affected_files=["outside/file.py"]
    )
    prop.generate_hash()
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec = builder.build_from_proposal(prop)
    assert spec.status == "BOUNDARY_CONFLICT"

def test_case_d_unsupported_operation():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[Requirement("r1", "desc")],
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["hack_system"])]
    )
    prop.generate_hash()
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec = builder.build_from_proposal(prop)
    assert spec.status == "TRANSFORMATION_UNSUPPORTED"

def test_case_e_dependency_invalid():
    # Builder by default doesn't add deps, so we inject one to test validator directly
    spec = TransformationSpecification(
        proposal_hash="hash", candidate_id="cand",
        requirements=[Requirement("r1", "desc")],
        items=[
            TransformationSpecItem("i1", "r1", "cand", ["move_files"], [], [TransformationDependency("missing_i2")], [], [], [])
        ]
    )
    builder = TransformationSpecificationBuilder(["move_files"], [])
    res = builder.validator.validate(spec)
    assert res.status == "SPECIFICATION_DEPENDENCY_INVALID"

def test_case_f_dependency_cycle():
    spec = TransformationSpecification(
        proposal_hash="hash", candidate_id="cand",
        requirements=[Requirement("r1", "desc")],
        items=[
            TransformationSpecItem("i1", "r1", "cand", ["move_files"], [], [TransformationDependency("i2")], [], [], []),
            TransformationSpecItem("i2", "r1", "cand", ["move_files"], [], [TransformationDependency("i1")], [], [], [])
        ]
    )
    builder = TransformationSpecificationBuilder(["move_files"], [])
    res = builder.validator.validate(spec)
    assert res.status == "SPECIFICATION_CYCLE"

def test_case_g_blocking_unknown():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[Requirement("r1", "desc")],
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["move_files"])],
        unknowns=["Missing some code info"] # "missing" makes it BLOCKING in our mock builder
    )
    prop.generate_hash()
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec = builder.build_from_proposal(prop)
    assert spec.status == "SPECIFICATION_INCOMPLETE"

def test_case_h_non_blocking_unknown():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[Requirement("r1", "desc")],
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["move_files"])],
        unknowns=["Just something minor"] # No "missing" or "incomplete"
    )
    prop.generate_hash()
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec = builder.build_from_proposal(prop)
    assert spec.status == "VALID"
    assert len(spec.unknowns) == 1
    assert spec.unknowns[0].classification == "NON_BLOCKING"

def test_case_i_semantic_identity_hash():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[Requirement("r1", "desc")],
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["move_files"])]
    )
    prop.generate_hash()
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec1 = builder.build_from_proposal(prop)
    spec2 = builder.build_from_proposal(prop)
    assert spec1.specification_hash == spec2.specification_hash

def test_case_j_target_change_hash():
    prop = TransformationProposal(
        proposal_id="p1", intent="intent", objective="obj", 
        requirements=[Requirement("r1", "desc")],
        items=[ProposalItem("i1", "r1", "REUSE", "desc", "cand", ["move_files"])]
    )
    prop.generate_hash()
    builder = TransformationSpecificationBuilder(["move_files"], ["foo/*"])
    spec1 = builder.build_from_proposal(prop)
    
    # Change target manually
    spec2 = builder.build_from_proposal(prop)
    spec2.items[0].targets.append(TransformationTarget("foo/bar.py"))
    spec2 = builder.validator.validate(spec2)
    
    assert spec1.specification_hash != spec2.specification_hash

def test_case_k_approval_mismatch():
    from core.execution.approval import ApprovalLifecycleManager
    app_mgr = ApprovalLifecycleManager()
    
    app = app_mgr.request_approval(
        "tx1", "cand", "wf", "pol", "bnd", ["move_files"],
        proposal_hash="phash", specification_hash="shash"
    )
    app_mgr.approve(app.approval_id)
    
    # Matching
    res1 = app_mgr.consume(app.approval_id, "wf", proposal_hash="phash", specification_hash="shash")
    assert res1 == "SUCCESS"
    
    app2 = app_mgr.request_approval(
        "tx2", "cand", "wf", "pol", "bnd", ["move_files"],
        proposal_hash="phash", specification_hash="shash"
    )
    app_mgr.approve(app2.approval_id)
    
    # Mismatch specification_hash
    res2 = app_mgr.consume(app2.approval_id, "wf", proposal_hash="phash", specification_hash="TAMPERED")
    assert res2 == "REJECTED: SPECIFICATION_MISMATCH"
