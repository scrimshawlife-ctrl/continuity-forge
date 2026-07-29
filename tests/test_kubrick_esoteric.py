import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "kubrick_helpers" / "src"))

from kubrick_helpers.esoteric import requested, select


INDEX = {
    "activation": {"explicit_terms": ["alchemy", "hidden symbolism"]},
    "selection_policy": {
        "primary_limit": 1,
        "secondary_limit": 2,
        "minimum_score": 0.55,
        "fail_closed": "NOT_COMPUTABLE",
        "audience_surface_default": "peripheral",
        "canon_status_default": "PROPOSED",
    },
    "concepts": {
        "alchemical_nigredo": {
            "tradition": "alchemy",
            "dramatic_operations": ["dissolve", "fragment", "descend"],
            "state_changes": ["identity_breakdown"],
            "vectors": ["material", "sound", "architecture"],
            "mutation": "decay changes ownership or consequence",
            "source_tier": "PRIMARY",
            "provenance": ["Zosimos"],
            "boundary": "Operational phase only.",
            "misuse_risks": ["generic darkness"],
        },
        "choronzon_drift": {
            "tradition": "modern_occult",
            "dramatic_operations": ["fragment", "contradict"],
            "state_changes": ["identity_drift"],
            "vectors": ["identity_state", "continuity"],
            "mutation": "tie divergence to invariant violation",
            "source_tier": "PRIMARY",
            "provenance": ["Thelemic writings"],
            "boundary": "Anomaly label only.",
            "misuse_risks": ["random surrealism"],
        },
    },
    "problem_routes": {
        "identity_breakdown": ["alchemical_nigredo", "choronzon_drift"]
    },
}


def test_esoteric_layer_does_not_activate_for_plain_dialogue_polish():
    assert requested({"request": "polish this dialogue"}, INDEX) is False


def test_explicit_flag_activates_layer():
    assert requested({"esoteric_encoding": True}, INDEX) is True


def test_missing_observable_evidence_fails_closed():
    result = select(
        {
            "esoteric_encoding": True,
            "dramatic_problem": "identity breakdown fragment descend",
            "desired_state_change": "dissolve the false identity",
        },
        INDEX,
    )
    assert result["status"] == "NOT_COMPUTABLE"
    assert result["selections"] == []
    assert any(item["reason"] == "observable evidence missing" for item in result["rejected_concepts"])


def test_selection_is_bounded_proposed_and_evidence_grounded():
    result = select(
        {
            "esoteric_encoding": True,
            "dramatic_problem": "identity breakdown fragment descend",
            "desired_state_change": "dissolve the false identity",
            "observable_evidence": ["wallpaper peels", "room tone loses its pulse"],
            "preferred_encoding_vectors": ["material", "sound"],
        },
        INDEX,
    )
    assert result["status"] == "SELECTED"
    assert 1 <= len(result["selections"]) <= 3
    assert result["canon_status"] == "PROPOSED"
    for item in result["selections"]:
        assert item["observable_evidence"]
        assert item["mutation_rule"]
        assert item["provenance"]
        assert item["tradition_boundary"]


def test_prohibited_concept_is_rejected():
    result = select(
        {
            "esoteric_encoding": True,
            "dramatic_problem": "identity breakdown fragment",
            "desired_state_change": "expose continuity drift",
            "observable_evidence": ["the scar changes sides between shots"],
            "prohibited_concepts": ["choronzon_drift"],
        },
        INDEX,
    )
    assert all(item["concept_id"] != "choronzon_drift" for item in result["selections"])
    assert {item["concept_id"] for item in result["rejected_concepts"]} == {"choronzon_drift"}


def test_active_ledger_grammar_receives_preference_without_bypassing_threshold():
    result = select(
        {
            "esoteric_encoding": True,
            "dramatic_problem": "identity breakdown",
            "desired_state_change": "dissolve and expose",
            "observable_evidence": ["the character removes a copied badge"],
            "active_project_grammars": ["alchemical_nigredo"],
        },
        INDEX,
    )
    assert result["governing_grammar"] == "alchemical_nigredo"
