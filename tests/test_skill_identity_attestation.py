import pytest
from core.skills.identity import SkillIdentity, CapabilityAttestation
from core.skills.models import Skill
from core.skills.registry import SkillRegistry

def test_skill_identity():
    ident = SkillIdentity("sk1", "skname", "1.0", "impl_abc", "man_abc")
    h = ident.calculate_identity_hash()
    assert h != ""

def test_capability_attestation():
    att = CapabilityAttestation("sk1", "1.0", "impl_abc", ["move_files", "copy_files"])
    h = att.generate_attestation_hash()
    assert att.verify()
    
    # Tamper capabilities
    att.capabilities.append("execute_shell")
    assert not att.verify()

def test_capability_drift():
    reg = SkillRegistry()
    skill1 = Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True)
    reg.register(skill1)
    
    skill2 = Skill("reuse_extraction", "loc", "desc", ["move_files", "execute_shell"], [], True, True)
    with pytest.raises(ValueError, match="CAPABILITY_DRIFT"):
        reg.register(skill2)
