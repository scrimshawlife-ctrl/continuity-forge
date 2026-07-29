# Continuity Forge Round-Trip Validation Example

**Step 1: Export from Kubrick**
- Produce symbolic_architecture using the continuity-forge-symbolic-export.schema.json.
- Include at minimum: motif_id, observed_form, provenance, mutation history, cinematic_encoding fields.
- Handoff via ingest with proper mutation envelope.

**Step 2: In Forge**
- Forge records motifs in continuity ledger.
- Shot contracts reference recurrence and geometric patterns.
- Project state (get_project_status) includes symbolic references.

**Step 3: Re-ingest / Next Session**
- Pull current project state from Forge.
- Re-hydrate project_symbolic_ledger from ledger.motifs.
- Verify:
  - motif_id and observed_form match exactly.
  - Mutation history is preserved.
  - Provenance is intact.
  - No new collisions introduced by Forge-side changes.

**Validation Test Criteria**
- motif identity survives.
- required mutation rules are still enforced on next proposal.
- symbolic_debt and saturation_score are correctly updated from Forge data.
- If Forge made changes (e.g., scene deletion), run revision_diff on re-hydrated ledger.

**Failure Mode Example**
- If a motif's observed_form is altered without mutation history, flag and require repair before new symbolic work.
