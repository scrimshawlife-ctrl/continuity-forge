## [0.7.1] - 2026-07-29
### Added — Autonomous Evolution from Use
- `scripts/evolve_from_use.py` — self-improvement engine
  - Aggregates retrieval receipts (auto-logged by retrieve script)
  - Incorporates project outcomes (success/failure signals)
  - Adjusts `confidence` in sidecars
  - Appends `usage_history` with performance data
  - Re-orders suggestions in `corpus-index.yaml` based on observed results
  - Emits auditable `evolution-*.json` receipts
- Auto-logging added to retrieval script (`references/usage/receipts/`)
- Seeded example usage data (receipts + outcomes)
- New procedures documented in SKILL.md under "Evolution from Use"
- Sidecars now carry usage-driven metadata

The corpus now improves from real application in projects and Forge workflows without manual curation for every pattern.

## [0.7.0] - 2026-07-29
### Added — Executable Retrieval (P0 of next campaign)
- `scripts/retrieve_symbolic_patterns.py` — deterministic retrieval helper
  - Loads index + sidecars
  - Scores with decomposition
  - Applies exclusions/prohibited
  - Emits structured retrieval_receipt
  - Fails closed below threshold
- Initial sidecar patterns in `references/patterns/` (9 high-value: alchemical nigredo, Kubrick monolith, Tarkovsky reflection, Bresson hands, Propp, Peirce, liminal, acousmatic, Denis marching)
- `evals/retrieval/` structure with inputs/ and expected/ golden fixtures
- 3 new formal tradition packs: Soviet montage, Japanese cinema, Animation
- SKILL.md documentation for the retrieval script

This begins the shift from reference skill to operational symbolic compiler.

## [0.6.2] - 2026-07-28 (further continuation)
### Added
- Additional genre packs: melodrama, comedy, low-budget/TV/short-form
- More populated schema examples (symbolic counterpoint, project ledger)
- Forge round-trip validation example and test
- Deeper film-pattern provenance depth for key examples (Kubrick Monolith, Tarkovsky, Bresson)
- Production feasibility test
- Expanded validation for round-trip and feasibility
- Updated SKILL.md with Forge round-trip procedure

### Expanded
- Genre and constrained-production guidance
- Transferable structure documentation in cinematic corpus

## [0.6.1] - 2026-07-28 (continuation after merge of #42)
### Added
- Populated schema examples (alchemical-nigredo, kubrick-monolith)
- Dedicated genre packs: horror, noir-thriller, science-fiction (under references/corpus/genre/)
- Concrete revision diff example (scene deletion)
- Additional validation tests for sequence/character arc and cultural review gates
- Concrete "How to Use" procedures in SKILL.md for scoring, ledger, sequence, character arc, revision, and handoff

### Expanded
- Film-pattern provenance depth examples integrated
- Cultural review trigger documentation and test
- Production feasibility notes in genre packs

This continues the P1/P2 hardening after the P0 merge.

## [0.6.0] - 2026-07-28
### Added — Symbolic Retrieval and Continuity Hardening (P0)
- Machine-readable schemas/ (symbolic-narrative-pattern, cinematic-pattern, transformation-grammar, narrative-affordance, symbolic-architecture, continuity-forge-symbolic-export)
- Retrieval scoring model with composite formula and NOT_COMPUTABLE threshold
- Negative retrieval / exclusion_profiles
- Project symbolic ledger (governing/supporting grammars, active/retired/prohibited motifs, symbolic_debt, saturation_score)
- Symbolic saturation control + SYMBOLIC_OVERLOAD
- Motif collision detection (REDUNDANT, CONTRADICTORY, etc.)
- Symbolic counterpoint rules
- Sequence-level symbolic_architecture and symbolic_character_arc compilation
- Symbolic revision diff engine
- Production feasibility weights
- Cultural review gates
- Corpus versioning and source_status (DRAFT → VALIDATED → DEPRECATED)
- Expanded cinematic corpus (genre packs, production scales, formal traditions: Soviet montage, Neorealism, Japanese, Hong Kong action, etc.)
- Film-pattern provenance depth (transferable_structure vs non_transferable_surface)
- references/retrieval-and-continuity.md
- Updated corpus-index.yaml with scoring, exclusions, ledger templates
- New validation cases for scoring, exclusion+collision, ledger+saturation+revision
- Forge round-trip validation expectations

### Changed
- SKILL.md now documents deterministic retrieval procedures as first-class
- All pattern work now expected to be schema-normalized + scored + collision-checked + ledger-tracked
- Cinematic examples now include production_cost and transferable vs surface distinction

This sprint converts the rich corpus into a reliable, auditable retrieval-and-continuity system.

## [0.5.0] - 2026-07-28
### Added
- Full provenance-linked Symbolic Narrative Pattern System
- `SymbolicNarrativePattern` core YAML schema with observed_structure, cinematic_affordances, mutation_rules, misuse_risks, and full source_records provenance
- Narrative Affordance Registry (BIND, DIVIDE, INITIATE, CONCEAL/REVEAL, INVERT, REPEAT, CONTAMINATE, MIRROR, SACRIFICE, CROSS, ENCLOSE, DESCEND, RETURN, HAUNT, ERASE, RESTORE + full mappings)
- Transformation Grammar Registry (alchemical processes, initiation, contamination, fragmentation, descent/return mapped to narrative + cinematic forms)
- Dedicated Cinematic Symbolism Corpus (techniques tracked as patterns with no fixed meanings)
- 10 corpus domains with starter PRIMARY/SCHOLARLY-anchored patterns (alchemical, ritual-liminal, cinematic)
- Source Hierarchy (PRIMARY / EARLY_COMMENTARY / SCHOLARLY / PRACTITIONER / COMPARATIVE / POPULAR / INTERNET)
- Cross-Tradition Relationship Types (HISTORICALLY_DERIVED, SHARED_FUNCTION, FORMAL_RESEMBLANCE, MODERN_SYNTHESIS, CONTESTED, UNSUPPORTED, etc.)
- Skill Retrieval Rules, Quality Gates, and 10 Validation Tests
- `corpus-usage.md`, `source-hierarchy.md`, `source-registry.md`, `cross-tradition-relationships.md`

### Changed
- kubrick positioned and documented as the primary/replacement symbolic cinematic skill
- Enhanced documentation across README, hermes docs, and internal references
- Updated retrieval discipline to prioritize dramatic problem → one primary grammar → at most two secondary → cinematic form → provenance

kubrick now provides a rigorous, auditable bridge from historically grounded symbolic systems to subtle scene, character, blocking, composition, editing, and sound structures.

# Changelog — kubrick

kubrick is the primary symbolic cinematic narrative engineering skill. It replaces the earlier scriptwriting skill as the recommended system for premise-to-production development with deep motif, geometric, and cinematic encoding.

## 0.4.0 — 2026-07-28 (Public-Ready Improvements)

### Major Polish & Completeness
- Fixed frontmatter to Hermes standards (description under 60 chars, author: Hermes only).
- Bumped version to 0.4.0.
- Added full evals/rubric.md with symbolic-specific scoring dimensions.
- Added strong symbolic regression cases:
  - test-motif-mutation.md + expected output
  - test-symbolic-slop.md (Gates M-W detection)
  - test-geometric-blocking.md
- Added corresponding expected outputs demonstrating observed-form-first, mandatory mutation, relational geometry, and anti-slop enforcement.
- Added Quick Reference section to SKILL.md.
- Restructured SKILL.md closer to canonical Hermes skill format.
- Added concrete YAML examples of symbolic_intent + motif_lifecycle + cinematic_encoding.
- Strengthened README with clearer value proposition and usage examples.
- Removed formerly scriptwriting language; positioned as the evolved replacement.
- Updated tags and triggers for clarity.
- Ensured all anti-slop gates M-W are documented and enforced.

### Retained Strengths
- Governing Law and three symbolic channels (Diegetic / Dramaturgical / Cinematic).
- observed_form-first discipline.
- Mandatory motif mutation on recurrence.
- Full Module 5B schemas (symbolic_intent, motif_lifecycle, shot_motif_ledger, cinematic_encoding, sonic_motif, correspondence_map).
- Continuity Forge handoff discipline.
- Anti-slop gates A-W.

## 0.3.0 — 2026-07-28
Initial public packaging of symbolic upgrade (Module 5B, M-W gates, Forge integration).

## Earlier
See scriptwriting history for base narrative engineering foundations (0.1.0-0.2.0). kubrick now supersedes that base for projects requiring cinematic symbolic precision.
