# Kubrick — Symbolic Cinematic Narrative Engineering System

**The primary skill for precise, motif-driven, geometrically rigorous cinematic storytelling.**

kubrick is the evolved replacement for earlier narrative engineering tools. It delivers production-ready scripts, scene contracts, and symbolic architecture that resist generic AI writing while creating latent, powerful visual and thematic systems.

## Quick Install (Standalone in Hermes)

```bash
# From inside this directory
./install.sh                 # installs to ~/.hermes/skills/kubrick
./install.sh creative        # installs to ~/.hermes/skills/creative/kubrick
```

Or manually:
```bash
cp -R . ~/.hermes/skills/kubrick
# or categorized
cp -R . ~/.hermes/skills/creative/kubrick
```

**Kubrick works completely on its own** — no continuity-forge installation required.

After install, restart Hermes and use natural language triggers (see SKILL.md).

## What Makes It Different

- **Observed first, meaning second**: Every motif begins with concrete, observable form before any interpretation.
- **Mandatory mutation**: No motif recurs identically unless stagnation is the dramatic point.
- **Three-channel symbolism**: Diegetic (objects/behavior), Dramaturgical (structure/choice), Cinematic (framing/geometry/rhythm) — power comes from crossing channels without explanation.
- **Provenance-linked Symbolic Narrative Pattern System**: Full `SymbolicNarrativePattern` schema, Narrative Affordance Registry, Transformation Grammar Registry, and 10+ domain packs grounded in PRIMARY/SCHOLARLY sources.
- **Executable Retrieval**: `scripts/retrieve_symbolic_patterns.py` provides deterministic, scored retrieval with exclusions, saturation awareness, and `NOT_COMPUTABLE` fallback.
- **Self-Evolution from Use**: The skill improves itself. Retrievals are auto-logged; project outcomes adjust pattern confidence, usage history, and index ordering via `scripts/evolve_from_use.py`.
- **Forge-native**: Produces clean `symbolic_architecture` and `cinematic_encoding` ready for Continuity Forge ledger and shot contracts.

## Key New Capabilities (0.7.x)

- Machine-readable pattern sidecars (`references/patterns/`)
- Deterministic retrieval with score decomposition and receipt emission
- Autonomous evolution engine that learns from real project/Forge usage
- Full support for project symbolic ledger, revision diffing, cultural review gates, and production feasibility

## Distribution & Installation

**Kubrick is a Hermes skill, not a Python package.**

It is **not** distributed via PyPI or included in the `continuity-forge` wheel. The core package only ships the production kernel (IR, compiler, ledger, harness, etc.). Skills live as self-contained directories.

### Recommended installation

From the continuity-forge repo root:

```bash
mkdir -p ~/.hermes/skills
cp -R skills/kubrick ~/.hermes/skills/
cp -R skills/hermes-continuity-forge ~/.hermes/skills/   # strongly recommended companion
```

Categorized layout (if your Hermes setup uses `creative/`):

```bash
cp -R skills/kubrick ~/.hermes/skills/creative/
```

You can also symlink for development:
```bash
ln -s "$(pwd)/skills/kubrick" ~/.hermes/skills/kubrick
```

### Why directory-only distribution?

- Skills contain markdown, schemas, examples, and small helper scripts that Hermes loads directly.
- **Kubrick works completely on its own inside Hermes**. No continuity-forge installation is required.
- Copy the skill directory and the scripts run self-contained with no external dependencies.

**Note for Continuity Forge users**: An optional `kubrick-helpers` Python package exists inside the continuity-forge repo (for CLIs and imports when using the full Python package). It is **not required** to use this skill in Hermes.

See `QUICKSTART.md` for the fastest way to get started.

See `docs/hermes/README.md` for general Hermes + Continuity Forge integration guidance.


## Quick Start

A minimal working example (brief + expected receipt) is included in `examples/minimal-retrieval-example.zip`.

Load `kubrick`.

**Retrieval example:**
```bash
python scripts/retrieve_symbolic_patterns.py --brief my-brief.yaml
```

**Evolution (after use):**
```bash
# After projects, drop outcomes in references/usage/outcomes/
python scripts/evolve_from_use.py
```

See SKILL.md for full procedures, prompts, and evolution workflow.

## Core Artifacts

- symbolic_intent contract
- motif_registry (observed_form + lifecycle)
- cinematic_encoding (relational + shot recurrence)
- symbolic_architecture (Forge handoff)
- retrieval_receipt
- evolution_receipt

## Companion

Use with `hermes-continuity-forge` for the full symbolic-to-production pipeline with memory and revision safety.

## Version

0.8.0 (Executable Retrieval + Self-Evolution)

See CHANGELOG.md for details.
