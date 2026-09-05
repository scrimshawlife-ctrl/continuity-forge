---
name: scriptwriting
description: "Narrative engineering system for multi-format scripts with Continuity Forge handoff for ledger, IR, and shot contracts."
version: 0.2.0
author: Hermes
platforms: [linux, macos, windows]
tags: [Scriptwriting, NarrativeEngineering, Screenplay, ContinuityForge, Ledger, AntiSlop, ProductionHandoff, Canon]
triggers:
  - develop screenplay
  - write script
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
---

# Scriptwriting — Narrative Engineering System (with Continuity Forge)

**Purpose**: A disciplined writers' room + script editor + continuity department. Develops ideas from premise to production-ready scripts that resist generic AI writing, continuity drift, character flattening, and exposition dumping. 

**Primary backend for canonical state**: Continuity Forge (ledger, Production IR, shot contracts, provenance). The skill produces high-quality narrative artifacts; Forge owns and enforces the canonical record.

This skill **does not** own canon, run the deterministic kernel, or claim production-ready media.

## When to Use

- Developing or refining premise, characters, world, theme, macrostructure, or sequences.
- Writing or expanding scenes from approved foundations (before or alongside Forge ingestion).
- Diagnosing problems, running anti-slop gates, or revision passes.
- Generating production packets or visual identities.
- Preparing material for handoff to Continuity Forge (compile, ingest under lease, shot contracts).
- Adapting between formats while preserving dramatic core.
- Any creative narrative work that will ultimately be governed by the Forge kernel.

**Companion skill**: `hermes-continuity-forge` (operator surface for MCP/CLI to the kernel).

## Prerequisites

Creative use is standalone: load this directory's SKILL.md and the relevant references.
Read `references/standalone-procedure.md` before routing, drafting or scoring.
For optional Forge handoff only, use a Python 3.12+ full editable checkout and the
operator skill; setup and MCP registration are in repo `docs/SETUP.md` and
`docs/hermes/README.md`. Package installation does not install skill directories.
Do not configure credentials, provider calls or a live store merely to write a scene.

## Request Routing & Modes

Read `references/standalone-procedure.md` for mode routing, ordered phases, artifact selection and the cited diagnosis rubric; load the named local narrative references for the selected mode.

When the goal is production use with Forge, prefer:
- DEVELOP → handoff to Forge ingest/compile
- DIAGNOSE / CONTINUITY → cross-check with Forge ledger via `get_project_status` / `audit_drift`

## Core Operating Principles

Read `references/standalone-procedure.md` for mode routing, ordered phases, artifact selection and the cited diagnosis rubric; load the named local narrative references for the selected mode.

**Forge-specific addition**: Once material is ingested to Forge under a lease + mutation contract, the Forge ledger + IR becomes the source of truth. Chat memory or local artifacts are proposals only until committed via Forge.

## Core Workflow (Phases)

Read `references/standalone-procedure.md` for mode routing, ordered phases, artifact selection and the cited diagnosis rubric; load the named local narrative references for the selected mode.

**12. Handoff to Continuity Forge (optional, explicit handoff)**

After foundations or scene contracts are approved:

- Use Forge to materialize canonical state:
  - `continuity-forge compile <script-or-outline> --out ...` (or MCP `compile_script`)
  - `acquire_write_lease` → `ingest_script` (with mutation envelope) 
  - `build_ledger`, `build_shot_contracts`
- Update local artifacts from Forge responses (hashes, scene/shot IDs, diagnostics).
- For revisions: always re-ingest with new rationale + expected_state_hash.
- Never treat local scene prose or character bibles as canon after Forge ingestion.

See `references/continuity-forge-integration.md` for exact commands and mutation contract usage.

## Anti-Slop Quality Gates

Read `references/standalone-procedure.md` for mode routing, ordered phases, artifact selection and the cited diagnosis rubric; load the named local narrative references for the selected mode.
- **Gate F-CANON (Forge Bypass)**: Generating or committing narrative changes without updating the Forge ledger/IR. Always hand off material changes.

## Output Selection Logic

Read `references/standalone-procedure.md` for mode routing, ordered phases, artifact selection and the cited diagnosis rubric; load the named local narrative references for the selected mode.
- Structured project brief (matches Forge intake)
- Scene contracts (feed `build_shot_contracts`)
- Approved canon list (for mutation envelopes)
- Production packets (can be cross-referenced with Forge shot contracts)

## Integration with Continuity Forge

**Handoff rules**:
- Creative development (this skill) produces **PROPOSED** or draft material.
- Only schema-validated deterministic output committed through Forge is canonical; narrative/model proposals are not promoted merely by attachment.
- Use leases + full mutation contract (`actor_id`, `authorization_scope`, `idempotency_key`, `rationale`) for any write path.
- Always surface Forge receipts/hashes in responses.
- Claim policy: material generated here is for development; final identity lives in Forge.

**Common patterns**:
- After DEVELOP: produce outline/character bible → `continuity-forge compile` or MCP ingest.
- After scene work: emit scene contract → feed to Forge shot compiler.
- For audit: run this skill's CONTINUITY + cross-check with Forge `audit_drift` / `get_project_status`.

See the companion skill `hermes-continuity-forge` for operator details (leases, PROPOSED candidates, controlled proof).

## Format-Specific Routing

Read `references/standalone-procedure.md` for mode routing, ordered phases, artifact selection and the cited diagnosis rubric; load the named local narrative references for the selected mode.

## Diagnosis Rubric

Use the anchored 1–5 rubric in `references/standalone-procedure.md`. When Forge is in play, also score "Forge alignment" (does the output produce clean ingestable material?).

## Validation Requirements

- Foundations approved.
- Anti-slop gates passed.
- Continuity ledger consistent (local + Forge).
- Any handoff includes mutation rationale and provenance.

## How to Run

Load this skill for creative narrative work. When ready for canonical state, route outputs through Continuity Forge (CLI or MCP via the companion operator skill).

Example:
```
Load scriptwriting.
Develop premise and first act outline for a short film.
Then hand off: "compile this to Continuity Forge and ingest under lease".
```

## References

- `references/story-structure.md`
- `references/character-and-dialogue.md`
- `references/scene-engineering.md`
- `references/continuity.md`
- `references/format-specific-guidance.md`
- `references/anti-slop-patterns.md`
- **`references/continuity-forge-integration.md`** (new — handoff commands, MCP patterns)
- `references/schemas/`
- `templates/`
- `evals/`

Companion: `hermes-continuity-forge` (in same repo).

## Quick Examples

**DEVELOP + Forge handoff**:
Vague idea → this skill produces strong logline + sequence outline + scene contracts → "Use continuity-forge compile and ingest_script with this material under lease."

**DIAGNOSE scene then Forge**:
Diagnose weak scene (gates + contract) → revise → emit updated scene contract → ingest delta to Forge.

**PRODUCTION handoff**:
Approved scenes → production packet + visual_identity from this skill → feed IDs/contracts into Forge shot system.

## Version History

See CHANGELOG.md in this skill and the main Continuity Forge repo.
