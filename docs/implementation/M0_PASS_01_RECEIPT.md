# M0 Pass 01 — Diagnostics, FDX, and Coverage

Campaign: `CONTINUITY_FORGE_COMPILER_FOUNDATION_001`
Issue: #1

## Validated implementation target

This pass advances the compiler spine with:

- typed diagnostic codes and severities
- validated source-span ordering
- explicit `CompileResult` and `CoverageReport` contracts
- orphan character-cue, empty-scene, missing-scene, malformed-FDX, unsupported-format, and source-coverage diagnostics
- FDX XML normalization into the canonical screenplay compiler
- explicit non-whitespace source coverage and silent-omission accounting
- golden-corpus determinism assertions across Fountain and FDX

## Local validation receipt

```yaml
branch: codex/m0-diagnostics-fdx-coverage
pytest: PASS
tests_passed: 9
deterministic_recompile: PASS
source_span_validation: PASS
fdx_ingestion: PASS
malformed_fdx_failure: PASS
silent_omission_gate: PASS
media_generation_added: false
```

## Required implementation files

- `packages/production_ir/src/continuity_forge_ir/models.py`
- `packages/production_ir/src/continuity_forge_ir/__init__.py`
- `packages/compiler/src/continuity_forge_compiler/compiler.py`
- `packages/compiler/src/continuity_forge_compiler/__init__.py`
- `tests/unit/test_compiler.py`
- `tests/golden/fixtures/minimal.fdx`
- `tests/golden/test_golden_corpus.py`

## Acceptance gates

- `pytest` passes with at least nine tests.
- Recompiling identical source yields byte-equivalent Production IR.
- Supported golden fixtures report zero silent omissions.
- Malformed FDX produces a typed error rather than an exception escape.
- Unsupported formats fail closed.
- No image, video, voice, or autonomous rewriting capability is introduced.

## Next bounded action

Implement this receipt on the current branch, preserve the public API compatibility of `compile_text()` and `compile_file()`, then update this receipt with the final commit SHA and CI result.
