# CONTINUITY_FORGE_POST_1_0_FOUNDATIONS_001

## Goal

Foundations after the mock controlled proof: durable filesystem persistence, provider
registry for swapping mock/real workers, and Temporal activity/worker wiring that can
run offline without a cluster.

## Scope

1. File-backed `RunStore` and `ProjectStore`
2. Provider registry (`mock` default; fail-closed real slots)
3. Temporal activities as pure callables + optional `temporalio` worker entrypoint
4. CLI hooks for persistence root and worker dry-run

## Exit gate

```yaml
file_store_roundtrip: PASS
provider_registry_mock_default: PASS
temporal_activities_offline: PASS
make_validate: PASS
```

## Explicit exclusions

- Production PostgreSQL/S3
- Live paid provider API calls in CI
- Multi-tenant OAuth
