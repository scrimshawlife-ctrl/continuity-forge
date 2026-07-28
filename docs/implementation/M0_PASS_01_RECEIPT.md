# M0 Pass 01 — Diagnostics, FDX, Coverage, and Read-Only Inspection

Campaign: `CONTINUITY_FORGE_COMPILER_FOUNDATION_001`
Issue: #1
PR: #2

## Implemented

This pass advances the deterministic compiler spine with:

- typed diagnostic codes and severities
- explicit `CompileResult` and `CoverageReport` contracts
- deterministic Fountain compilation with stable IDs
- UTF-8 byte-accurate source coverage
- FDX normalization and typed malformed-XML failure
- schema-enforced Fountain/FDX API inputs
- package-path divergence repair under `packages/production_ir`
- protocol-neutral read-only MCP inspection tools
- executable golden corpus gates
- Fountain transitions with precedence regression coverage
- parentheticals and multiline dialogue blocks
- single-line Fountain title-page metadata with source provenance

## Authority rules preserved

- Source screenplay text remains immutable input.
- Models and agents do not write canonical state.
- Metadata is stored separately from narrative atoms.
- Metadata does not receive a synthetic scene ID.
- MCP exposes no mutation tools.
- Unsupported grammar remains explicitly deferred.

## Current validation state

```yaml
branch: codex/m0-diagnostics-fdx-coverage
static_audit: PASS
package_path_divergence: REPAIRED
malformed_fdx_failure: TYPED
unsupported_format_behavior: FAIL_CLOSED
mcp_surface: READ_ONLY
golden_corpus:
  deterministic_serialization: REQUIRED
  zero_silent_omissions: REQUIRED
  atom_and_metadata_provenance: REQUIRED
github_actions:
  status: BLOCKED
  classification: RUNNER_TERMINATES_BEFORE_CHECKOUT
  recorded_steps: 0
media_generation_added: false
```

## Supported clean-input grammar

See `docs/compiler/M0_SUPPORTED_GRAMMAR.md` for the executable grammar boundary.

## Remaining M0 work

- Execute Ruff, mypy, pytest, coverage, API, MCP, and corpus gates on a functioning runner.
- Expand only those grammar constructs that receive fixtures and deterministic tests.
- Version and export the Production IR JSON Schema.
- Complete the final M0 acceptance receipt before review-ready transition.

## Scope exclusions preserved

- image or video generation
- voice generation
- visual-bible generation
- autonomous adaptation or rewriting
- direct agent database mutation
- feature-length readiness claims
