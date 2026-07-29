# Product workflow

Creative-production journey for Continuity Forge operators (filmmakers, writers,
producers, continuity reviewers). Engineering vocabulary is progressive disclosure
only (Settings → Developer).

## Personas

| Persona | Needs |
|---------|--------|
| Writer / producer | Import script, see scenes and characters quickly |
| Continuity supervisor | Resolve conflicts, lock wardrobe/props, track timeline |
| Generative pipeline integrator | Export provider-neutral scene/shot packages |
| Developer | Proof, hashes, leases, MCP, raw JSON |

## Primary workflow

1. **Create Project** — title, production type, script (paste / file / sample).
2. **Import Script** — `.fountain`, `.fdx`, `.txt` only.
3. **Analyze Script** — deterministic breakdown + continuity extraction.
4. **Review Scenes and Continuity** — scene cards, entry/exit, shot cards, bible tabs.
5. **Resolve Conflicts** — explicit choices; no silent resolution.
6. **Prepare Scene for Generation** — provider-neutral scene package.
7. **Generate or Export** — export works without a provider.
8. **Review Generated Results** — decisions preserve lineage; canon only via validated mutations.
9. **Advance Canonical Continuity State** — through existing MutationEnvelope / store paths, not UI display alone.

## Information architecture

Primary navigation:

- Projects
- Scenes
- Continuity
- Generate
- Review
- Export

Plus project switcher and Settings (Developer).

## Screen descriptions

| Screen | Dominant action |
|--------|-----------------|
| Empty | New Project |
| Project | Analyze Script |
| Analysis complete | Review Breakdown |
| Scenes | Prepare Scene for Generation |
| Continuity | Lock values / resolve conflicts |
| Generate | Export Package |
| Review | Accept / Repair / Regenerate / Reject (intent) |
| Export | Markdown or JSON packages |

## State models

**Project phases:** EMPTY → IMPORTED → ANALYZING → NEEDS_REVIEW | CONFLICTED → READY → GENERATING → REVIEWING → APPROVED; STALE / ERROR as needed.

**Scene readiness:** Needs Review, Conflict, Ready, Generating, Generated, Approved, Stale.

**Shot status:** DRAFT, READY, SUBMITTED, GENERATED, VALIDATION_FAILED, REPAIR_PROPOSED, APPROVED, REJECTED, STALE.

**Provenance:** SCRIPT, INFERRED, USER_LOCKED, GENERATED, CONFLICT, STALE (text + icon).

## Terminology

Prefer: Project, Script, Scene, Shot, Character, Location, Wardrobe, Prop, Continuity, Generate, Review, Export.

Avoid in default UI: IR, receipt, claim, lease, state hash, mutation, MCP, Temporal, tenant.

## Error states

Friendly errors explain what happened, whether data was preserved, next steps, and expandable technical detail.

## Accessibility

Keyboard navigation, visible focus, semantic headings, labels, status alerts, no color-only state, reduced-motion support, mobile bottom nav + sticky Analyze Script.

## Advanced / Developer

Settings → Developer: API connection, provider notes, state hashes, raw JSON, mock pipeline test, leases/approvals pointer.
