from pathlib import Path

from continuity_forge_compiler import compile_file, compile_text
from continuity_forge_ledger import build_continuity_ledger
from continuity_forge_shots import ConstraintStrength, compile_shot_contracts

FIXTURES = Path(__file__).parents[1] / "golden" / "fixtures"


def test_shot_contracts_cover_every_scene_deterministically() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    first = compile_shot_contracts(document)
    second = compile_shot_contracts(document)
    assert first == second
    assert len(first.contracts) == len(document.scenes)
    assert {contract.scene_id for contract in first.contracts} == {
        scene.scene_id for scene in document.scenes
    }


def test_shot_contracts_require_atoms_and_hard_constraints() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    bundle = compile_shot_contracts(document)
    for contract in bundle.contracts:
        assert contract.required_atom_ids
        assert contract.start_state_hash
        assert contract.end_state_hash
        assert "image" in contract.provider_capabilities
        assert any(check.check_id == "hard_constraints" for check in contract.validation_checks)
        hard = [item for item in contract.constraints if item.strength == ConstraintStrength.HARD]
        assert hard


def test_shot_contracts_encode_prop_and_forbid_constraints() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    bundle = compile_shot_contracts(document)
    codes = {
        constraint.code.value
        for contract in bundle.contracts
        for constraint in contract.constraints
    }
    assert "require_prop" in codes or "require_character" in codes
    assert "forbid_prop" in codes or "require_wardrobe_state" in codes


def test_shot_contracts_accept_prebuilt_ledger() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    ledger = build_continuity_ledger(document)
    bundle = compile_shot_contracts(document, ledger=ledger)
    assert bundle.script_id == document.script_id
    assert bundle.ledger_hash


def test_state_hashes_stable_for_same_document_key() -> None:
    text = (FIXTURES / "continuity.fountain").read_text(encoding="utf-8")
    first = compile_shot_contracts(compile_text(text, document_key="shots-stable"))
    second = compile_shot_contracts(compile_text(text, document_key="shots-stable"))
    assert [c.start_state_hash for c in first.contracts] == [
        c.start_state_hash for c in second.contracts
    ]
    assert [c.shot_id for c in first.contracts] == [c.shot_id for c in second.contracts]
