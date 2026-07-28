# Architecture index

- [Production Harness Architecture](PRODUCTION_HARNESS_ARCHITECTURE.md)
- [ADR-0001: Adopt a deterministic production harness](../adr/ADR-0001-production-harness.md)
- [Install & setup](../SETUP.md)
- [Hermes integration](../hermes/README.md)
- [Hermes operator skill](../../skills/hermes-continuity-forge/SKILL.md)
- [Mutation contract (operator skill)](../../skills/hermes-continuity-forge/references/mutation-contract.md)

The harness architecture is authoritative for agent, workflow, provider, approval, and canonical-state boundaries. Hermes is the preferred operator agent; it must not own canon.

## Trust boundary (Phase 1)

| Edge | Rule |
|------|------|
| Write contract | `MutationEnvelope` on every mutating API/MCP path |
| Project concurrency | `expected_state_hash` = `ProjectRecord.state_hash` on re-ingest |
| Lease exclusivity | Single active holder per document; non-holder cannot mutate |
| Providers | Must not import `continuity_forge_persistence` or operator `ProjectStore` |
| Models | PROPOSED only until reviewed and committed |

Enforced in code under `packages/operator` and by
`tests/unit/test_architecture_boundaries.py` / `tests/unit/test_operator.py`.
