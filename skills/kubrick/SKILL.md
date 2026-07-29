---
name: kubrick
description: "Symbolic narrative engineering with executable retrieval and self-evolution from use."
version: 0.8.0
author: Hermes
platforms: [linux, macos, windows]
tags: [Kubrick, NarrativeEngineering, SymbolicDramaturgy, CinematicEncoding, MotifMutation, VisualMotif, Geometry, ArchetypeFunction, Screenplay, ContinuityForge, Ledger, AntiSlop, ProductionHandoff, Canon]
triggers:
  - develop screenplay
  - write script
  - kubrick style
  - symbolic narrative
  - cinematic dramaturgy
  - motif engineering
  - geometric composition
  - screenplay for continuity forge
  - tv pilot
  - short film script
  - youtube video script
  - podcast script
  - diagnose script
  - continuity audit
  - rewrite scene
  - dialogue polish
  - production packet
  - scene contract
  - logline
  - beat sheet
  - character bible
  - premise engineering
  - handoff to continuity forge
  - ingest to forge
  - symbolic intent contract
---

# Kubrick — Symbolic Cinematic Narrative Engineering System (with Continuity Forge)

**Purpose**: A disciplined writers' room + script editor + cinematic symbolic engineer. Develops ideas from premise to production-ready scripts using precise symbolic dramaturgy, relational composition, motif lifecycle, archetypal function, and visual encoding. Resists generic AI writing, continuity drift, character flattening, exposition dumping, occult collage, and one-to-one symbolism.

**Standalone by default**. This skill runs fully independently inside Hermes. It can optionally hand off clean artifacts to Continuity Forge when that system is also installed. The skill produces high-quality narrative artifacts with latent symbolic operating system; Forge owns and enforces the canonical record.

This skill **does not** own canon, run the deterministic kernel, or claim production-ready media.

## Governing Law (Symbolic Physics)

> **A symbol should alter the conditions under which a scene is interpreted without requiring the audience to consciously identify it.**

Symbolism operates as:
motif enters → acquires contextual association → recurs under altered pressure → changes formal behavior → converges with character choice → becomes retrospectively legible.

**Not**: symbol appears → symbol is explained → audience receives meaning.

## Three Symbolic Channels

| Channel           | Function                                                                      |
| ----------------- | ----------------------------------------------------------------------------- |
| **Diegetic**      | Objects, places, gestures, costumes, architecture and sounds inside the world |
| **Dramaturgical** | Repeated situations, choices, roles, reversals and causal structures          |
| **Cinematic**     | Framing, geometry, movement, rhythm, light, sound placement and editing       |

A motif becomes powerful when it crosses channels without being explicitly identified.

## When to Use

- Developing or refining premise, characters, world, theme, macrostructure, or sequences with symbolic depth.
- Writing or expanding scenes that require cinematic precision, motif mutation, geometric blocking, or hidden correspondence.
- Diagnosing problems, running anti-slop gates (A–W), or revision passes with symbolic pressure.
- Generating production packets or visual identities grounded in symbolic architecture.
- Preparing material for handoff to Continuity Forge (compile, ingest under lease, shot contracts).
- Adapting between formats while preserving dramatic core and latent symbolic grammar.
- Any creative narrative work that will ultimately be governed by the Forge kernel.

**Companion skill**: `hermes-continuity-forge` (operator surface for MCP/CLI to the kernel).

## Prerequisites

- Continuity Forge installed and in PATH:
  ```bash
  pip install -e '.[dev]'   # from continuity-forge repo
  continuity-forge --help
  ```
- (Recommended) `continuity-forge-mcp` configured in Hermes for tool use.
- Optional: `humanizer` for final voice.

Env for Forge (pass to any MCP/terminal calls):
```bash
export CF_STORE_ROOT="$HOME/.local/share/continuity-forge"
# export CF_PROVIDER=mock
```

## Request Routing & Modes

Same as base (DEVELOP, DRAFT, DIAGNOSE, REVISE, POLISH, CONTINUITY, PRODUCTION, ADAPT) plus symbolic-specific routing.

When the goal is production use with Forge, prefer:
- DEVELOP → handoff to Forge ingest/compile
- DIAGNOSE / CONTINUITY → cross-check with Forge ledger via `get_project_status` / `audit_drift`
- Symbolic work always produces `symbolic_intent`, `motif_registry`, `cinematic_encoding` alongside standard artifacts.

## Core Operating Principles

(Structure Before Pages, Drama Is Change Under Pressure, Behavior Before Explanation, Causality, Compression, Specificity, Approved Material Is Canon.)

**New Symbolic Layer Additions**:
- Symbolism conditions the field of meaning rather than transmitting fixed messages.
- Archetypes are candidate functional patterns, not declared identities.
- Ritual structure modeled through repetition, cadence, affective load, fixed roles, persistence, participatory behavior.
- Geometry, numbers, correspondences separated into observable structure / interpretive overlay / speculative attribution.
- Every motif must mutate under pressure; identical recurrence only if stagnation is the point.
- Cross-tradition equivalence requires explicit boundary guards.

**Forge-specific addition**: Once material is ingested to Forge under a lease + mutation contract, the Forge ledger + IR becomes the source of truth. Chat memory or local artifacts are proposals only until committed via Forge.

## Core Workflow (Phases)

1–11. (Intake → Premise → Characters → World → Theme → Macrostructure → Sequences/Beats → Scene Engine → Dialogue/Prose → Continuity Ledger → Revision) — same as base, now augmented with symbolic tracking.

**Module 5B — Symbolic Dramaturgy and Cinematic Encoding** (new primary module, integrated throughout):

Before or alongside scene work:
- Define `symbolic_intent` contract (dramatic_function required; reject purely aesthetic/esoteric symbolism).
- Build `motif_registry` using `symbolic_packet` (observed_form first, never leading with "meaning: X").
- Engineer `motif_lifecycle` with explicit mutation on every recurrence.
- Map `archetypal_functions` (observable behaviors + spatial/relationship/transformation roles; explicit naming disallowed by default).
- Record `tradition_boundaries` and `correspondence_map` (private/hidden where appropriate).
- Translate to `cinematic_encoding`: composition_patterns (relational, not cliché), geometric_patterns, blocking_patterns, camera_patterns, shot_recurrence (with mutation ledger), edit_cadence, sonic_motifs, production_design_states.

**12. Handoff to Continuity Forge (critical phase)**

After foundations or scene contracts (now including symbolic architecture) are approved:
- Use Forge to materialize canonical state:
  - `continuity-forge compile <script-or-outline> --out ...` (or MCP `compile_script`)
  - `acquire_write_lease` → `ingest_script` (with mutation envelope)
  - `build_ledger`, `build_shot_contracts`
- Update local artifacts from Forge responses (hashes, scene/shot IDs, diagnostics).
- For revisions: always re-ingest with new rationale + expected_state_hash.
- Never treat local scene prose, character bibles, or symbolic packets as canon after Forge ingestion.

See `references/continuity-forge-integration.md` for exact commands and mutation contract usage.

See `references/symbolic-dramaturgy.md` for full schemas, gates, and procedural guidance.

## Anti-Slop Quality Gates

A–L (see `references/anti-slop-patterns.md`) plus M–W for symbolic work:

- **Gate M (Symbol Explanation)**: Any line that explains a symbol the scene has already made legible.
- **Gate N (Occult Collage)**: Arbitrary mixtures without governing grammar.
- **Gate O (Symbolic Redundancy)**: All channels screaming the same meaning at once.
- **Gate P (One-to-One Symbolism)**: bird = freedom, red = danger, etc. without contextual transformation.
- **Gate Q (Repetition Without Mutation)**: Recurring images that do not change.
- **Gate R (Archetype Costume)**: Iconography without functional enactment.
- **Gate S (Tradition Flattening)**: Unsupported cross-cultural equivalence.
- **Gate T (Numerology Inflation)**: Arbitrary numbers with no structural effect.
- **Gate U (Symbolic Supremacy)**: Symbolism compromises causality, agency, clarity, tone, credibility, or feasibility.
- **Gate V (Mystery by Obscurity)**: Ambiguity from withheld causal information rather than open relation.
- **Gate W (Premature Closure)**: Explicit confirmation of the "correct" interpretation.

Additional Forge gate (carried over): Gate M (Forge Bypass) — generating changes without Forge ledger update.

## Output Selection Logic

Same as base. Preferred handoff artifacts:
- Structured project brief (matches Forge intake)
- Scene contracts (feed `build_shot_contracts`)
- Approved canon list (for mutation envelopes)
- Production packets (cross-referenced with Forge shot contracts)
- **New**: `symbolic_architecture`, `cinematic_encoding`, motif registry, recurrence/inversion/convergence plans, hidden correspondence map (when active)

## Integration with Continuity Forge

**Handoff rules**:
- Creative development (this skill) produces **PROPOSED** or draft material (including symbolic proposals).
- Forge ingestion makes it canonical.
- Use leases + full mutation contract (`actor_id`, `authorization_scope`, `idempotency_key`, `rationale`) for any write path.
- Always surface Forge receipts/hashes in responses.
- Claim policy: material generated here is for development; final identity lives in Forge.

**Common patterns**:
- After DEVELOP: produce outline/character bible + symbolic_intent + initial motif registry → `continuity-forge compile` or MCP ingest.
- After scene work: emit scene contract + cinematic_encoding → feed to Forge shot compiler.
- For audit: run this skill's CONTINUITY + cross-check with Forge `audit_drift` / `get_project_status`.

See the companion skill `hermes-continuity-forge` for operator details (leases, PROPOSED candidates, controlled proof).

## Format-Specific Routing

Same as base, with the addition that Forge's shot contracts and ledger are format-aware. Symbolic density and cinematic encoding expectations scale with format (features support richer recurrence and geometric layering; shorts demand extreme compression and precision).

## Diagnosis Rubric

Same 1-5 rubric. When Forge is in play, also score "Forge alignment". When symbolic work active, additionally score:
- Motif mutation and lifecycle fidelity
- Channel crossing without explanation
- Relational composition (vs. cliché)
- Tradition boundary respect
- Ambiguity preserved vs. obscurity

## Validation Requirements

- Foundations approved.
- Anti-slop gates passed (A–W as applicable).
- Continuity ledger consistent (local + Forge).
- Any handoff includes mutation rationale and provenance.
- Symbolic packets use observed_form first; dramatic_function defined; mutations specified.
- Cross-tradition work has explicit boundaries recorded.


## Quick Reference

**New Deterministic Tools (v0.5.0+)**
- "Score these patterns for this dramatic problem and character using the retrieval model"
- "Run exclusion profile for identity fragmentation on this premise"
- "Initialize project symbolic ledger with governing grammar X"
- "Check saturation and collisions for this sequence"
- "Produce symbolic revision diff for this scene deletion"
- "Generate symbolic character arc for this internal change using pressure operations"
- "Apply symbolic counterpoint: image vs dialogue"
- "Export symbolic_architecture using Forge round-trip schema"



## Evolution from Use (Self-Improving Corpus)

Kubrick is designed to improve itself through repeated application.

**Core Mechanism**
- Every retrieval automatically logs a receipt to `references/usage/receipts/`.
- After Forge handoff, revision, or project review, record outcomes in `references/usage/outcomes/`.
- Run the evolution engine: `python scripts/evolve_from_use.py`

**What Evolves**
- Pattern `confidence` is raised for patterns that repeatedly deliver clean results (low debt, successful mutations, no collisions).
- `usage_history` is appended to sidecars with performance data.
- `corpus-index.yaml` re-orders suggestions based on observed success.
- Weak or overused patterns have confidence lowered and may be flagged for deprecation or mutation rule changes.

**How to Feed It**
1. After a project or significant sequence:
   ```bash
   # record outcome
   echo '{"pattern_id": "alchemical_nigredo_putrefaction", "project": "my-film-042", "outcome": "success", "signals": ["clean revision", "Forge accepted"]}' > references/usage/outcomes/$(date +%s).json
   ```
2. Run evolution:
   ```bash
   python scripts/evolve_from_use.py
   ```
3. The engine produces `references/evolution/evolution-*.json` receipts.

**Integration with Ledger**
Project symbolic ledgers can be copied to `references/usage/ledgers/` for richer signals (saturation trends, debt accumulation, revision diff results).

**Governance**
- Evolution only adjusts confidence and history. Structural changes (new patterns, new grammars) still require human review.
- All changes are timestamped and accompanied by an evolution receipt.
- You can disable auto-logging or run evolution in dry-run mode.

This turns every real use of the skill (especially when paired with Continuity Forge) into training data that sharpens future retrieval.

**Key Commands / Behaviors**
- "Develop this premise with strong symbolic architecture and motif lifecycle" → DEVELOP + symbolic_intent + motif_registry (observed first) + cinematic_encoding.
- "Diagnose this scene for motif mutation and geometric pressure" → DIAGNOSE with rubric + Gates A–W.
- "Rewrite this scene but keep the circular blocking and broken-circle motif locked" → REVISE with canon tracking + symbolic constraints.
- "Give me production handoff with cinematic encoding and shot recurrence ledger" → PRODUCTION + symbolic_architecture.
- "Define symbolic intent and lifecycle for the recurring unlit exit sign" → explicit Module 5B output.

**Core Symbolic Artifacts**
- symbolic_intent (dramatic_function required)
- symbolic_packet / motif_registry (observed_form first)
- motif_lifecycle (mutation on every recurrence required)
- cinematic_encoding (relational geometry, blocking, shot_recurrence)
- symbolic_architecture (for Forge handoff)

**Required Before Symbolic Work**
- symbolic_intent contract
- observed_form defined
- dramatic_function specified


## How to Run

Load this skill for creative narrative work with cinematic/symbolic precision. When ready for canonical state, route outputs through Continuity Forge (CLI or MCP via the companion operator skill).

Example:
```
Load kubrick.
Develop premise and first act outline for a short film with strong visual motif lifecycle and geometric blocking.
Define symbolic_intent and initial motifs.
Then hand off: "compile this to Continuity Forge and ingest under lease with symbolic architecture".
```

## References

- `references/symbolic-dramaturgy.md` (Module 5B — core symbolic laws, schemas, lifecycle, cinematic grammar, gates M–W, correspondence maps, esoteric embedding through constraint)

- `references/symbolic-dramaturgy.md` (Module 5B core)
- `references/symbolic-narrative-patterns.yaml` (core schema)
- `references/narrative-affordance-registry.md`
- `references/transformation-grammar-registry.md`
- `references/cinematic-symbolism-corpus.md`
- `references/source-hierarchy.md`, `source-registry.md`, `cross-tradition-relationships.md`
- `references/corpus-usage.md` (retrieval rules, gates, validation)
- `references/corpus-index.yaml` (lightweight retrieval index)
- `references/corpus/` (domain packs with provenance)

- `references/story-structure.md`
- `references/character-and-dialogue.md`
- `references/scene-engineering.md`
- `references/continuity.md`
- `references/format-specific-guidance.md`
- `references/anti-slop-patterns.md` (A–W gates)
- `references/continuity-forge-integration.md` (handoff commands, MCP patterns)
- `schemas/`
- `templates/`
- `evals/`

Companion: `hermes-continuity-forge` (in same repo).

## Quick Examples

**DEVELOP + Forge handoff (symbolic)**:
Vague idea → this skill produces strong logline + sequence outline + scene contracts + `symbolic_intent` + `motif_registry` (observed forms) + `cinematic_encoding` (relational compositions, geometric patterns, shot recurrence plan) → "Use continuity-forge compile and ingest_script with this material under lease."

**DIAGNOSE scene then Forge**:
Diagnose weak scene (gates A–W + contract) → revise motif mutation and blocking → emit updated scene contract + symbolic delta → ingest delta to Forge.

**PRODUCTION handoff**:
Approved scenes → production packet + visual_identity (grounded in symbolic architecture and geometric patterns) from this skill → feed IDs/contracts into Forge shot system.

## Version History

See CHANGELOG.md in this skill and the main Continuity Forge repo.

**0.3.0** — Assimilated Symbolic Narrative Upgrade: added MODULE 5B (Symbolic Dramaturgy and Cinematic Encoding), full motif lifecycle, symbolic_packet, intent contracts, shot/blocking grammar, relational composition, hidden correspondence, archetypal function (no naming), tradition guards, Gates M–W, sonic/edit symbolism, esoteric-through-constraint. Renamed to kubrick. Renamed and upgraded from prior scriptwriting base.
