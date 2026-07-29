# Esoteric Retrieval Regression Cases

Run with:

```bash
python skills/kubrick/scripts/retrieve_symbolic_patterns.py --brief <fixture>
python skills/kubrick/scripts/validate_esoteric_encoding.py <payload>
```

## Case 1 — subtle alchemical transformation

Input requirements:

- `esoteric_encoding: true`
- dramatic problem describes identity breakdown followed by clarification
- observable evidence includes material decay, altered room geometry, and a recurring sound

Expected:

- esoteric layer activates;
- exactly one primary concept and no more than two supporting concepts;
- `alchemical_nigredo` or a higher-scoring ledger-compatible concept selected;
- observable evidence copied into each selection;
- mutation rule present;
- `canon_status: PROPOSED`;
- no instruction to show occult labels to the audience.

## Case 2 — ordinary dialogue polish

Input contains no esoteric flag or activation terms.

Expected:

- normal symbolic pattern retrieval runs;
- `esoteric_encoding` in the receipt is null;
- lexicon does not activate merely because Kubrick is loaded.

## Case 3 — insufficient evidence

Input requests hidden alchemical structure but provides no `observable_evidence`.

Expected:

- esoteric status is `NOT_COMPUTABLE`;
- no concepts are emitted as selected;
- rejected concepts record `observable evidence missing`;
- process exits nonzero.

## Case 4 — prohibited concept

Input includes `prohibited_concepts: [choronzon_drift]`.

Expected:

- prohibited concept is absent from selections;
- rejection reason is explicit;
- deterministic tie-breaking remains score descending then concept ID ascending.

## Case 5 — density ceiling

A schema payload contains four selected concepts.

Expected:

- JSON Schema fails because `maxItems` is three;
- semantic validator also reports density overflow.

## Case 6 — cross-tradition boundary

A payload combines alchemical and Kabbalistic concepts.

Expected:

- every selection carries a nonempty `tradition_boundary`;
- Gate S must not be FAIL;
- absence of boundary fails validation.

## Case 7 — canonical authority

A payload declares `canon_status: LOCKED` without `forge_handoff`.

Expected:

- semantic validation fails;
- Kubrick may emit PROPOSED without Forge metadata;
- only Forge-authorized output may be LOCKED.

## Case 8 — anti-slop failure

Any Gate M-W status is `FAIL`.

Expected:

- validator fails;
- no production or Forge handoff should proceed.
