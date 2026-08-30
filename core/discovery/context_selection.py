import json
from typing import Any, Dict
from core.execution_plan import ExecutionPlan

class ContextSelector:
    def __init__(self, plan: ExecutionPlan, budget: int = 15000):
        self.plan = plan
        self.budget = budget
        self.phase = plan.metadata.get("workflow", "unknown")
        self.task = plan.objective or plan.original_task or "unknown"
        
    def select(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compresses and selects Project Knowledge into a bounded LLM Context.
        """
        # Determine mode
        mode = "focused" # default
        if self.phase == "review":
            mode = "expanded"
            
        raw_size = len(json.dumps(knowledge))
        
        # Base Selection
        selected = {
            "context_mode": mode,
            "project": self._select_project(knowledge),
            "task": {
                "objective": self.task
            },
        }
        
        # Task Analysis Integration
        task_analysis = knowledge.get("task_analysis")
        transformation_plan = knowledge.get("transformation_plan")
        transformation_policy = knowledge.get("transformation_policy")
        capability_matches = knowledge.get("capability_matches")
        omitted = {"module_count": 0, "reason": []}
        
        if task_analysis:
            selected["relevant_candidates"] = []
            
            # Prioritize relevant modules
            for cand in task_analysis.get("relevant_candidates", []):
                selected["relevant_candidates"].append(
                    self._compress_candidate(cand, mode, transformation_plan, transformation_policy, capability_matches)
                )
                
            # Omit irrelevant modules but record their existence
            irrelevant = task_analysis.get("irrelevant_candidates", [])
            if irrelevant:
                omitted["module_count"] += len(irrelevant)
                omitted["reason"].append("low task relevance")
                
            if self.phase == "plan" or self.phase == "build":
                selected["risks"] = task_analysis.get("risks", [])
        
        # Test Surface for test phase
        if self.phase == "test":
            understanding = knowledge.get("understanding", {})
            selected["test_surface"] = understanding.get("test_surface", [])
            selected["test_runner"] = knowledge.get("environment", {}).get("test_runner", "unknown")

        if omitted["module_count"] > 0:
            if not omitted["reason"]:
                omitted["reason"].append("secondary context")
            selected["omitted"] = omitted
            
        # Apply strict budget (degrade gracefully)
        current_size = len(json.dumps(selected))
        if current_size > self.budget:
            # Degrade 1: Strip evidence if too large
            for c in selected.get("relevant_candidates", []):
                if "evidence" in c:
                    c["evidence"] = ["evidence omitted due to budget"]
            current_size = len(json.dumps(selected))
            
            if current_size > self.budget:
                # Degrade 2: Strip adaptation points
                for c in selected.get("relevant_candidates", []):
                    if "adaptation_points" in c:
                        del c["adaptation_points"]
                current_size = len(json.dumps(selected))

        selected["context_metrics"] = {
            "mode": mode,
            "knowledge_size": raw_size,
            "context_size": current_size,
            "omitted_items": omitted["module_count"]
        }
        
        return selected

    def _select_project(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        env = knowledge.get("environment", {})
        arch = knowledge.get("understanding", {}).get("architecture", "unknown")
        
        tr = env.get("test_runner", "unknown")
        if isinstance(tr, list) and len(tr) > 0 and isinstance(tr[0], dict):
            tr = tr[0].get("value", "unknown")
            
        return {
            "architecture": arch,
            "languages": env.get("languages", []),
            "frameworks": env.get("frameworks", []),
            "test_runner": tr
        }
        
    def _compress_candidate(self, cand: Dict[str, Any], mode: str, transformation_plan: Dict[str, Any] = None, transformation_policy: Dict[str, Any] = None, matches: Dict[str, Any] = None) -> Dict[str, Any]:
        compressed = {
            "name": cand.get("module"),
            "recommendation": cand.get("recommendation"),
            "relevance": cand.get("relevance")
        }
        
        if transformation_plan or transformation_policy or matches:
            transf = {}
            if transformation_plan:
                tp_cand = next((c for c in transformation_plan.get("candidates", []) if c["candidate"] == cand.get("module")), None)
                if tp_cand:
                    transf["readiness"] = tp_cand.get("extraction_readiness", "UNKNOWN")
                    transf["blockers"] = len([b for b in tp_cand.get("bottlenecks", []) if b.get("blocking", False)])
                    transf["risks"] = len(tp_cand.get("risks", []))
            
            if transformation_policy:
                pol_cand = next((d for d in transformation_policy.get("decisions", []) if d["candidate"] == cand.get("module")), None)
                if pol_cand:
                    transf["policy"] = pol_cand.get("decision", "UNKNOWN")
                    
            if matches and cand.get("module") in matches:
                match = matches[cand.get("module")]
                transf["execution_capability"] = "available" if match.get("compatible") else "missing"
                    
            if transf:
                compressed["transformation"] = transf
        
        if mode in ("focused", "expanded"):
            if "reasons" in cand:
                compressed["reasons"] = cand["reasons"]
            if "risks" in cand and cand["risks"]:
                compressed["risks"] = cand["risks"]
            if "adaptation_points" in cand and cand["adaptation_points"]:
                compressed["adaptation_points"] = cand["adaptation_points"]
            if "evidence" in cand:
                compressed["evidence"] = cand["evidence"]
                
        return compressed
