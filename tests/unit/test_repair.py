from continuity_forge_compiler import compile_text
from continuity_forge_providers import Authority, ProviderGateway
from continuity_forge_repair import run_repair_loop, validate_candidate
from continuity_forge_shots import compile_shot_contracts


def test_repair_loop_recovers_after_forced_failure() -> None:
    document = compile_text(
        "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nGo.\n",
        document_key="repair",
    )
    contract = compile_shot_contracts(document).contracts[0].model_dump(mode="json")
    result = run_repair_loop(contract, seed="r", fail_first=True, max_attempts=3)
    assert result.status == "accepted_proposed"
    assert len(result.attempts) >= 2
    assert result.attempts[0].validation.passed is False
    assert result.attempts[-1].validation.passed is True
    assert result.accepted_candidate is not None
    assert result.accepted_candidate.authority == Authority.PROPOSED


def test_hard_constraint_failure_is_detected() -> None:
    document = compile_text(
        "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nGo.\n",
        document_key="repair2",
    )
    contract = compile_shot_contracts(document).contracts[0].model_dump(mode="json")
    bad = ProviderGateway().generate_for_shot(contract, seed="x", force_missing_entities=True)
    report = validate_candidate(contract, bad)
    assert report.passed is False
    assert any(f.code == "missing_required_entity" for f in report.findings)
