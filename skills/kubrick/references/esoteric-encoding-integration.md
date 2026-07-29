# Esoteric Encoding Integration Contract

This contract operationalizes `esoteric-alchemical-encoding-lexicon.md` and `../schemas/esoteric-encoding.schema.yaml` inside Kubrick without changing canon ownership.

## Load conditions

Load the lexicon when a request includes any of the following:

- symbolic architecture, hidden symbolism, esoteric structure, alchemy, occult structure, ritual structure;
- motif lifecycle, archetypal function, sacred geometry, planetary pressure, elemental grammar;
- scene transformation modeled as phase change;
- subtle cinematic encoding across image, sound, blocking, editing, props, materials, or continuity;
- diagnosis of symbolic drift, occult collage, one-to-one symbolism, or tradition flattening.

Do not load it for ordinary copyediting or dialogue polish unless symbolic architecture is already active.

## Required procedure

1. Read the dramatic problem and current observable scene state.
2. Define the desired state change.
3. Retrieve one governing concept and no more than two secondary concepts.
4. Record provenance and tradition boundaries.
5. Translate each concept into observable encoding vectors.
6. Define recurrence mutation, inversion, payoff, and residue where applicable.
7. Validate against Gates M-W.
8. Emit `esoteric-encoding.schema.yaml`-conformant data.
9. Mark the result `PROPOSED`.
10. Use Continuity Forge mutation controls before any canonical write.

## Deterministic selection order

```text
DRAMATIC_PROBLEM
-> OBSERVED_STATE
-> DESIRED_CHANGE
-> TRANSFORMATION_GRAMMAR
-> PRIMARY_CONCEPT
-> OPTIONAL_SECONDARY_CONCEPTS
-> CINEMATIC_VECTORS
-> MUTATION_RULE
-> BOUNDARY_CHECK
-> ANTI_SLOP_CHECK
-> FORGE_HANDOFF
```

## Selection constraints

- Prefer a concept already present in the project's symbolic ledger.
- Prefer one tradition with deeper internal coherence over several visually similar traditions.
- Prefer an observable operation over a named metaphysical claim.
- Prefer material, spatial, sonic, temporal, or behavioral encoding over explicit dialogue.
- Prefer mutation of an existing motif over introduction of a new motif.
- Reject a concept when evidence is insufficient; output `NOT_COMPUTABLE`.

## Required output extension

When active, append this block to `symbolic_architecture`:

```yaml
esoteric_encoding:
  schema_version: "1.0.0"
  dramatic_problem: string
  observed_scene_state: string
  desired_state_change: string
  governing_grammar:
    grammar_id: string
    tradition: string
    dramatic_function: string
    provenance: [string]
    boundary: string
  selections:
    - concept_id: string
      tradition: string
      dramatic_function: string
      encoding_vectors: [string]
      observable_evidence: [string]
      mutation_rule: string
      inversion_condition: string | null
      payoff_condition: string | null
      residue: string | null
      audience_visibility: peripheral | readable | foreground | delayed
      confidence: 0.0
      provenance: [string]
      tradition_boundary: string
  rejected_concepts:
    - concept_id: string
      reason: string
  canon_status: PROPOSED
```

## Rune mapping

These are procedural names, not autonomous code modules unless implemented separately.

```text
RUNE.PRIMA_MATERIA(scene)   -> extract unresolved narrative potential
RUNE.SOLVE(scene)           -> decompose into canonical cinematic units
RUNE.SEPARATE(scene)        -> distinguish essential state from incidental detail
RUNE.CORRESPOND(scene, work)-> detect micro/macro structural correspondence
RUNE.TRUE_NAME(character)   -> resolve invariant identity across transformation
RUNE.GENIUS_LOCI(location)  -> resolve persistent rules and intelligence of place
RUNE.TALISMAN(prop)         -> track accumulated causal and symbolic charge
RUNE.ATHANOR(sequence)      -> measure and preserve transformative pressure
RUNE.CONJUNCTION(elements)  -> test lawful union of separated forces
RUNE.DISTILL(draft)         -> remove noise while preserving dramatic essence
RUNE.COAGULATE(spec)        -> convert abstract canon into renderable material form
RUNE.OUROBOROS(sequence)    -> detect recursive or self-causing structures
RUNE.CHORONZON(generation)  -> detect uncontrolled fragmentation and drift
RUNE.HERMETIC_SEAL(state)   -> lock validated canonical conditions
RUNE.TIKKUN(discontinuity)  -> repair fragments without erasing provenance
RUNE.RUBEDO(sequence)       -> verify transformation has become embodied action
```

## Canon and provenance

- Kubrick proposes symbolic structures.
- Continuity Forge owns canonical acceptance and mutation receipts.
- The lexicon does not establish historical equivalence among traditions.
- Concept names may remain private metadata; audience-facing work should expose effects, not labels.
- Any interpretation unsupported by observable evidence must remain `SPECULATIVE` or `NOT_COMPUTABLE`.
