# Kubrick Quickstart

Kubrick is a **standalone Hermes skill** for precise symbolic narrative engineering. It works without Continuity Forge.

## 1. Install

```bash
# From inside this folder
./install.sh                 # → ~/.hermes/skills/kubrick
./install.sh creative        # → ~/.hermes/skills/creative/kubrick
```

Or manually:
```bash
cp -R . ~/.hermes/skills/kubrick
```

Restart Hermes after installing.

## 2. Basic Usage (Retrieval)

Give it a brief:

```bash
python scripts/retrieve_symbolic_patterns.py --brief evals/retrieval/inputs/sample_melodrama_lowbudget.yaml
```

It outputs a `retrieval_receipt` with ranked symbolic patterns, scores, and provenance.

## 3. Evolution (Self-improvement)

After using the skill on real projects, drop receipts/outcomes into `references/usage/` and run:

```bash
python scripts/evolve_from_use.py
```

This updates pattern confidence and ordering based on actual results.

## 4. Triggers (in Hermes)

- "develop screenplay"
- "kubrick style"
- "symbolic narrative"
- "motif engineering"
- "handoff to continuity forge"
- "diagnose script"

See `SKILL.md` for the full list and detailed procedures.

## Next Steps

- Read `README.md` for full capabilities and distribution notes.
- Explore `references/patterns/` and `evals/` for examples.
- See `examples/minimal-retrieval-example.zip` for a tiny input + expected pair.

**This skill runs completely independently inside Hermes.**
