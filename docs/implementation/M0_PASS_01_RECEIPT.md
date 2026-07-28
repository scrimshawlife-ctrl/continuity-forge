# M0 Pass 01 — Diagnostics, FDX, and Coverage

Campaign: `CONTINUITY_FORGE_COMPILER_FOUNDATION_001`
Issue: #1
PR: #2

## Implemented

- typed diagnostic codes and severities
- explicit `CompileResult` and `CoverageReport` contracts
- deterministic Fountain compilation with stable IDs
- FDX XML normalization through the canonical compiler path
- malformed FDX fail-closed result using `CF_FDX_MALFORMED`
- source coverage measured in UTF-8 bytes
- unsupported file formats rejected rather than silently parsed
- API source format constrained to `fountain | fdx`
- API contract migrated from `ScriptDocument` to `CompileResult`
- package-path divergence repaired so canonical IR remains under `packages/production_ir`
- duplicate `packages/ir` implementation removed

## Static gate audit

```yaml
branch: codex/m0-diagnostics-fdx-coverage
head: b0f52a8b094050a7c95474ccddd660491f8ee45a
mergeable: true
mypy_type_gap_current_scene_id: repaired
malformed_fdx_exception_escape: repaired
unsupported_api_format_fallback: repaired
api_contract_envelope_mismatch: repaired
utf8_coverage_accounting: repaired
package_path_divergence: repaired
media_generation_added: false
```

## CI state

GitHub-hosted jobs are currently terminating before checkout and expose zero executed steps. This is classified separately from repository code status until runner allocation or account-level Actions configuration is restored.

The workflow now emits explicit environment, install, lint, typing, test, and coverage steps when a runner begins execution.

## Acceptance gates remaining

- GitHub runner executes checkout and exposes step logs.
- Ruff passes.
- Mypy strict passes.
- Pytest and coverage pass.
- Full golden corpus reaches zero silent omissions for supported constructs.
- Read-only MCP surface is implemented and contract-tested.

## Scope exclusions preserved

- image or video generation
- voice generation
- visual-bible generation
- autonomous adaptation or rewriting
- direct agent database mutation
- feature-length readiness claims
