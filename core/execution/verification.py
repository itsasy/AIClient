from dataclasses import dataclass
from typing import Dict, Any, List
from pathlib import Path
import subprocess
from core.execution.transaction import ExecutionRecord

@dataclass
class VerificationResult:
    check: str
    status: str # PASS, FAIL, SKIPPED, UNKNOWN
    evidence: str = ""
    command: str = ""
    exit_code: int = 0

class VerificationEngine:
    def __init__(self, target_root: Path):
        self.target_root = target_root
        
    def verify(self, transaction: ExecutionRecord) -> List[VerificationResult]:
        results = []
        for req in transaction.postconditions:
            if req == "imports_resolve":
                results.append(self._verify_imports(transaction))
            elif req == "candidate_tests_pass":
                results.append(self._verify_tests(transaction))
            else:
                results.append(VerificationResult(req, "UNKNOWN", f"Verification method for {req} not implemented"))
        return results
        
    def _verify_imports(self, transaction: ExecutionRecord) -> VerificationResult:
        # Simplistic verification: compile all python files in the destination
        # to catch syntax errors or basic import errors if evaluated
        dest_files = transaction.files_changed + transaction.files_created
        py_files = [f for f in dest_files if f.endswith('.py')]
        if not py_files:
            return VerificationResult("imports_resolve", "SKIPPED", "No python files to verify")
            
        for f in py_files:
            abs_path = self.target_root / f
            if abs_path.exists():
                try:
                    # Just run py_compile. A real implementation might use a static analyzer.
                    subprocess.run(
                        ["python", "-m", "py_compile", str(abs_path)],
                        cwd=str(self.target_root),
                        check=True,
                        capture_output=True,
                        text=True
                    )
                except subprocess.CalledProcessError as e:
                    return VerificationResult("imports_resolve", "FAIL", e.stderr, e.cmd, e.returncode)
                    
        return VerificationResult("imports_resolve", "PASS", "All modified python files compiled successfully")

    def _verify_tests(self, transaction: ExecutionRecord) -> VerificationResult:
        # Extremely simplistic. If there's a tests/ test_ candidate .py, run pytest on it.
        # Otherwise skip or fail.
        # If candidate tests are strictly required, it fails if it can't find them.
        cmd = ["pytest"]
        # In a real environment, we'd find the exact test path. Let's just run pytest locally on the destination root or module tests.
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.target_root),
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                return VerificationResult("candidate_tests_pass", "PASS", "Tests passed", " ".join(cmd), 0)
            elif res.returncode == 5: # No tests collected
                return VerificationResult("candidate_tests_pass", "FAIL", "No tests found", " ".join(cmd), 5)
            else:
                return VerificationResult("candidate_tests_pass", "FAIL", res.stdout[-500:], " ".join(cmd), res.returncode)
        except Exception as e:
            return VerificationResult("candidate_tests_pass", "FAIL", str(e))
