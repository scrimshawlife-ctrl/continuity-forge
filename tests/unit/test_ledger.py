from pathlib import Path

from continuity_forge_compiler import compile_file, compile_text
from continuity_forge_ledger import EntityKind, FactKind, build_continuity_ledger

FIXTURES = Path(__file__).parents[1] / "golden" / "fixtures"


def test_ledger_is_deterministic_for_continuity_fixture() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    first = build_continuity_ledger(document)
    second = build_continuity_ledger(document)
    assert first == second
    assert first.script_id == document.script_id
    assert first.source_hash == document.source_hash


def test_ledger_registers_characters_locations_props_wardrobe_injury() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    ledger = build_continuity_ledger(document)
    by_kind = {kind: [] for kind in EntityKind}
    for entity in ledger.entities:
        by_kind[entity.kind].append(entity.normalized_name)

    assert "mara" in by_kind[EntityKind.CHARACTER]
    assert "eli" in by_kind[EntityKind.CHARACTER]
    assert any("safehouse" in name for name in by_kind[EntityKind.LOCATION])
    assert "red keycard" in by_kind[EntityKind.PROP] or "keycard" in by_kind[EntityKind.PROP]
    assert "brass compass" in by_kind[EntityKind.PROP] or "compass" in by_kind[EntityKind.PROP]
    assert "jacket" in by_kind[EntityKind.WARDROBE]
    assert any("forearm" in name or "cut" in name for name in by_kind[EntityKind.INJURY])


def test_ledger_records_enter_exit_and_scene_contracts() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    ledger = build_continuity_ledger(document)
    assert len(ledger.scene_contracts) == len(document.scenes)
    assert any(contract.entries for contract in ledger.scene_contracts)
    assert any(contract.exits for contract in ledger.scene_contracts)
    kinds = {fact.kind for fact in ledger.facts}
    assert FactKind.ENTERS in kinds
    assert FactKind.EXITS in kinds
    assert FactKind.APPEARS_IN in kinds


def test_ledger_links_setup_and_payoff() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    ledger = build_continuity_ledger(document)
    assert ledger.setup_payoff_links
    assert any(fact.kind == FactKind.PLANTS for fact in ledger.facts)
    assert any(fact.kind == FactKind.PAYS_OFF for fact in ledger.facts)
    for link in ledger.setup_payoff_links:
        setup = next(fact for fact in ledger.facts if fact.fact_id == link.setup_fact_id)
        payoff = next(fact for fact in ledger.facts if fact.fact_id == link.payoff_fact_id)
        assert setup.kind == FactKind.PLANTS
        assert payoff.kind == FactKind.PAYS_OFF
        assert setup.subject_entity_id == payoff.subject_entity_id == link.entity_id


def test_every_fact_has_atom_provenance() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    ledger = build_continuity_ledger(document)
    atom_ids = {
        atom.atom_id
        for atom in [
            *document.preamble,
            *(atom for scene in document.scenes for atom in scene.atoms),
        ]
    }
    for fact in ledger.facts:
        assert fact.atom_ids
        assert all(atom_id in atom_ids for atom_id in fact.atom_ids)


def test_absent_prop_is_recorded() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    ledger = build_continuity_ledger(document)
    absent = [fact for fact in ledger.facts if fact.kind == FactKind.ABSENT]
    assert absent
    assert any("keycard" in fact.value for fact in absent)


def test_entity_ids_stable_across_rebuild() -> None:
    text = (FIXTURES / "continuity.fountain").read_text(encoding="utf-8")
    first = build_continuity_ledger(compile_text(text, document_key="ledger-stable"))
    second = build_continuity_ledger(compile_text(text, document_key="ledger-stable"))
    assert {entity.entity_id for entity in first.entities} == {
        entity.entity_id for entity in second.entities
    }
