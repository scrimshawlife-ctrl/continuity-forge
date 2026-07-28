# Agent operating contract

## Authority

- Source screenplay text is immutable input.
- Deterministic parser output is canonical only after schema validation.
- Frontier-model output is always `PROPOSED` until reviewed and committed.
- Agents must not write directly to persistence or bypass command validation.

## Active campaign

Read `docs/campaigns/CONTINUITY_FORGE_COMPILER_FOUNDATION_001.md` before changing code.

## Scope discipline

Do not add generation providers, visual-bible systems, timeline editing, or autonomous rewriting during M0.

## Completion receipt

Every implementation pass must report:

- files changed
- tests added or updated
- commands executed
- passing/failing gates
- unresolved ambiguity
- next bounded action
