from core.execution.specification import TransformationSpecification
from core.execution.proposal import TransformationProposal
from core.analysis.structural_model import ProjectStructuralModel
from core.analysis.semantic_model import SemanticProgramModel
from core.execution.operation_registry import OperationRegistry
from core.execution.candidates import (
    TransformationCandidate, CandidateEvidence, CandidateImpact, CandidateRisk,
    CandidateUnknown, CandidateItem, CandidateTarget, CandidateComparison, CandidateSelectionRecommendation
)

class TransformationCandidateGenerator:
    def __init__(self, registry: OperationRegistry):
        self.registry = registry

    def generate(self, proposal: TransformationProposal, spec: TransformationSpecification, struct: ProjectStructuralModel, sem: SemanticProgramModel) -> list[TransformationCandidate]:
        candidates = []
        
        # In a multi-candidate scenario (P17), a spec can yield multiple candidates if multiple candidates are in spec.items.
        # But P25 says "Given what the user wants to achieve, what transformation strategies are possible".
        # We might have alternative candidates for the same goal, or multiple candidates combined.
        # For this prototype, we'll map each spec "candidate" directly, and also project alternatives.
        
        # We group items by spec candidate_id
        cands_by_id = {}
        for item in spec.items:
            cid = item.candidate_id
            if cid not in cands_by_id:
                cands_by_id[cid] = []
            cands_by_id[cid].append(item)
            
        for cid, items in cands_by_id.items():
            cand = TransformationCandidate(candidate_id=cid)
            
            # 1. Traceability Evidence
            cand.evidence = CandidateEvidence(
                proposal_hash=proposal.proposal_hash,
                specification_hash=spec.specification_hash,
                structural_analysis_hash=struct.analysis_hash,
                semantic_analysis_hash=sem.semantic_analysis_hash,
                traceability_links=[item.req_id for item in items]
            )
            if not proposal.proposal_hash or not spec.specification_hash:
                cand.status = "CANDIDATE_TRACEABILITY_FAILURE"
                
            # 2. Unknown Propagation
            for unk in sem.unknowns:
                cand.unknowns.append(CandidateUnknown(code=unk.code, explanation=unk.explanation, blocking=unk.blocking))
                if unk.blocking:
                    cand.status = "CANDIDATE_BLOCKED"
                    
            cand.impact = CandidateImpact()
            ops_count = 0
            
            # 3. Items and Targets
            for item in items:
                # Naive mapping of spec operation to CandidateItem action
                action_type = "MODIFY"
                if "move" in item.operations[0]: action_type = "MOVE"
                elif "create" in item.operations[0]: action_type = "CREATE"
                elif "delete" in item.operations[0]: action_type = "DELETE"
                
                c_item = CandidateItem(item_id=item.item_id, action_type=action_type)
                
                for t in item.targets:
                    confidence = "CONFIRMED"
                    if t.path not in struct.modules and t.path not in [m.path for m in struct.modules.values()]:
                        # File/module not found in structural model -> unknown
                        confidence = "UNKNOWN"
                    c_item.targets.append(CandidateTarget(target_type=t.target_type, target_id=t.path, confidence=confidence))
                    cand.impact.files_affected.append(t.path)
                    
                    if confidence == "UNKNOWN":
                        cand.unknowns.append(CandidateUnknown("TARGET_UNKNOWN", f"Target {t.path} not found in structural model", False))
                
                for op in item.operations:
                    if op not in self.registry.handlers and op != "NO_OP":
                        cand.status = "TRANSFORMATION_UNSUPPORTED"
                    c_item.required_operations.append(op)
                    ops_count += 1
                    
                cand.items.append(c_item)

            # 4. Impact Analysis (Indirect & Semantic)
            for file_path in cand.impact.files_affected:
                # Find the module for this file
                mod_name = None
                for m_name, m_mod in struct.modules.items():
                    if m_mod.path == file_path:
                        mod_name = m_name
                        break
                if mod_name and mod_name in sem.modules:
                    cand.impact.modules_affected.append(mod_name)
                    # Check reverse dependencies in semantic model
                    for sym_name, impact in sem.impacts.items():
                        if sym_name.startswith(f"{mod_name}."):
                            cand.impact.symbols_affected.append(sym_name)
                            cand.impact.indirect_impact.extend(impact.indirect_consumers)
                            cand.impact.indirect_impact.extend(impact.direct_consumers)
                            cand.impact.unknown_impact.extend(impact.unknown_consumers)
            
            # 5. Risk Analysis
            score = "LOW"
            factors = []
            if len(cand.impact.files_affected) > 5:
                score = "MEDIUM"
                factors.append("Many files affected")
            if len(cand.impact.indirect_impact) > 10:
                score = "HIGH"
                factors.append("High indirect impact")
            if any(u.blocking for u in cand.unknowns):
                score = "BLOCKED"
                factors.append("Blocking unknowns present")
            elif len(cand.unknowns) > 0:
                if score == "LOW": score = "MEDIUM"
                factors.append("Unknowns present")
                
            if cand.status == "TRANSFORMATION_UNSUPPORTED":
                score = "BLOCKED"
                factors.append("Unsupported operations required")

            cand.risk = CandidateRisk(score=score, factors=factors)
            cand.generate_hash()
            candidates.append(cand)
            
        return candidates

class CandidateComparator:
    def compare(self, candidates: list[TransformationCandidate]) -> CandidateComparison:
        comp = CandidateComparison()
        
        # Pairwise cross-candidate analysis
        for i, c1 in enumerate(candidates):
            for j, c2 in enumerate(candidates):
                if i >= j: continue
                
                # Check dependencies (e.g. c2 uses something c1 produces)
                # Check conflicts (e.g. c1 modifies file X, c2 deletes file X)
                c1_files = set(c1.impact.files_affected) if c1.impact else set()
                c2_files = set(c2.impact.files_affected) if c2.impact else set()
                
                intersection = c1_files.intersection(c2_files)
                if intersection:
                    comp.cross_candidate_conflicts.append(f"{c1.candidate_id} and {c2.candidate_id} conflict on {list(intersection)}")
                    
        return comp

    def recommend(self, candidates: list[TransformationCandidate]) -> CandidateSelectionRecommendation:
        if not candidates:
            return CandidateSelectionRecommendation("", "No candidates", "", "", "", "", "NOT_RECOMMENDED")
            
        valid = [c for c in candidates if c.status == "VALID" and c.risk and c.risk.score != "BLOCKED"]
        if not valid:
            return CandidateSelectionRecommendation("", "All candidates blocked or invalid", "", "", "", "", "NOT_RECOMMENDED")
            
        # Sort by risk, then by number of unknowns, then by impact
        def rank(c):
            risk_val = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(c.risk.score, 4)
            return (risk_val, len(c.unknowns), len(c.impact.files_affected))
            
        valid.sort(key=rank)
        
        best = valid[0]
        if len(valid) > 1 and rank(valid[0]) == rank(valid[1]):
            return CandidateSelectionRecommendation(
                best.candidate_id, "Equivalent top candidates", "Multiple candidates match criteria",
                best.risk.score, str(len(best.impact.files_affected)), str(len(best.unknowns)), "TIE"
            )
            
        return CandidateSelectionRecommendation(
            best.candidate_id,
            "Lowest risk and unknowns",
            f"Traceable to {best.evidence.proposal_hash}",
            best.risk.score,
            f"{len(best.impact.files_affected)} files",
            f"{len(best.unknowns)} unknowns",
            "RECOMMENDED"
        )
