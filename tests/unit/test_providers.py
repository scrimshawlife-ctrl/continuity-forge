from continuity_forge_compiler import compile_text
from continuity_forge_providers import Authority, ProviderGateway
from continuity_forge_shots import compile_shot_contracts


def test_mock_candidate_is_deterministic_and_proposed() -> None:
    document = compile_text(
        "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nGo.\n",
        document_key="prov",
    )
    contract = compile_shot_contracts(document).contracts[0].model_dump(mode="json")
    gateway = ProviderGateway()
    first = gateway.generate_for_shot(contract, seed="7")
    second = gateway.generate_for_shot(contract, seed="7")
    assert first == second
    assert first.authority == Authority.PROPOSED
    assert first.content_hash
    assert first.lineage["shot_id"] == str(contract["shot_id"])
