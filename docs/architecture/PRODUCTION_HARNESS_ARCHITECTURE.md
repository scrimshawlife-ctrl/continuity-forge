# Continuity Forge Production Harness Architecture

Status: **ADOPTED**  
Version: **0.1**

## Decision

Continuity Forge is a deterministic cinematic-production kernel surrounded by a model-agnostic orchestration harness.

Models generate proposals and media. Continuity Forge governs story truth, continuity, workflow state, approvals, validation, provenance, and revision impact.

```yaml
system_class: cinematic_production_harness
canonical_kernel: deterministic
model_layer: replaceable_and_non_authoritative
workflow_runtime: durable
operator_protocol: MCP
primary_operator_agent: Hermes
secondary_operator_client: OpenClaw
```

## Architecture

```text
OPERATOR
  -> Hermes / OpenClaw / Product UI
  -> MCP + authenticated REST command plane
  -> CONTINUITY FORGE
       - screenplay compiler
       - Production IR
       - canonical continuity ledger
       - durable workflow harness
       - policy and approval engine
       - model capability router
       - artifact and provenance store
       - evaluation and repair engine
  -> isolated reasoning, generation, validation, and media workers
```

## Authority boundary

### Deterministic kernel owns

- Source screenplay and revisions
- Narrative atoms and exact source spans
- Stable IDs and content hashes
- Entity identity registry
- Chronology and causal graph
- Character knowledge and emotional-state records
- Wardrobe, injury, prop, and spatial state
- Scene entry and exit contracts
- Script-coverage accounting
- Approval state and waivers
- Artifact lineage and revision dependencies

### Models may

- Propose entity aliases
- Propose setup/payoff and causal edges
- Propose scene and shot plans
- Diagnose validation failures
- Recommend least-destructive repairs
- Produce image, video, voice, and editorial candidates

### Models must not

- Mutate canonical state directly
- Rewrite source-script text silently
- Promote observations into canon
- Waive continuity failures
- Approve identity or location bibles
- Bypass cost, rights, or provenance controls

## Three-layer execution model

### 1. Deterministic kernel

Python services and PostgreSQL own typed commands, canonical state, invariants, and content-addressed artifacts.

### 2. Durable production harness

Temporal owns retries, timeouts, human approval waits, provider outages, idempotency, cancellation, compensation, concurrency, and resume-after-failure behavior.

### 3. Bounded agentic reasoning

Direct frontier-model calls or optional LangGraph subgraphs own ambiguous interpretation, shot-planning proposals, evaluation, diagnosis, and repair proposals.

Agent checkpoints are never canonical film state.

## Generator-evaluator loop

```text
CANONICAL STATE
  -> SHOT CONTRACT COMPILER
  -> GENERATOR
  -> DETERMINISTIC VALIDATORS
  -> MULTIMODAL EVALUATOR
       PASS -> COMMIT ACCEPTED ARTIFACT
       FAIL -> REPAIR PLAN -> REGENERATE / INPAINT / RETIME / REVOICE
```

Each shot contract contains:

- Required narrative atoms
- Hard continuity constraints
- Soft creative targets
- Prohibited additions or mutations
- Start-state and end-state hashes
- Provider capability requirements
- Validation tests and thresholds

## Brain, harness, hands, session, and canon

```yaml
brain:
  implementation: frontier_reasoning_model_or_Hermes
  authority: proposal_only
harness:
  implementation: Continuity_Forge_control_plane
  authority: workflow_and_policy
hands:
  implementation:
    - image_worker
    - video_worker
    - voice_worker
    - lip_sync_worker
    - ffmpeg_worker
    - vision_validation_worker
session:
  implementation: append_only_event_log_plus_workflow_history
canon:
  implementation: Production_IR_plus_continuity_ledger
```

## MCP boundary

### Resources

```text
cf://projects/{id}/script
cf://projects/{id}/production-ir
cf://projects/{id}/continuity-ledger
cf://scenes/{id}/manifest
cf://shots/{id}/validation
cf://projects/{id}/coverage-report
```

### Read tools

```text
cf.get_project_status
cf.list_scenes
cf.inspect_scene
cf.inspect_character_state
cf.get_compile_diagnostics
cf.audit_coverage
cf.audit_drift
cf.get_revision_impact
```

### Mutating tools

```text
cf.propose_scene_plan
cf.approve_bible_asset
cf.queue_generation
cf.request_repair
cf.waive_validation_failure
cf.commit_revision
```

Every mutation requires:

- Actor identity
- Authorization scope
- Idempotency key
- Expected-state hash
- Command version
- Rationale

## Hermes and OpenClaw

Hermes is the preferred operator agent. OpenClaw is an alternate client, notification surface, or scheduled-automation layer.

Neither owns canonical project memory, workflow history, provider credentials, or artifact lineage. Both use the same MCP and REST contracts.

A write lease prevents simultaneous uncontrolled agent mutations:

```yaml
write_lease:
  holder: agent_session_id
  scope: project_or_scene
  expires_at: timestamp
```

## Human approval thresholds

Approval is required for:

- Character and location identity locks
- Material script interpretation
- Narrative omission or adaptation
- Continuity waivers
- High-cost generation campaigns
- Canon-changing revisions
- Low-confidence final acceptance

Automatic within approved bounds:

- Retry timed-out provider calls
- Recompute validation features
- Rerun deterministic validators
- Regenerate a failed candidate within approved manifest and budget
- Produce proxy media and thumbnails

## Storage and observability

```yaml
canonical_state: PostgreSQL
workflow_history: Temporal
artifact_bytes: S3_compatible_content_addressed_storage
vector_index: pgvector
media_processing: FFmpeg
required_telemetry:
  - append_only_command_and_event_log
  - model_request_and_response_trace
  - provider_and_seed_provenance
  - artifact_lineage
  - validation_receipts
  - cost_ledger
  - approval_and_waiver_history
```

## Implementation sequence

```text
M0 COMPILER SPINE
-> M1 CONTINUITY LEDGER
-> M2 SHOT CONTRACT COMPILER
-> M3 DURABLE HARNESS / TEMPORAL
-> M4 MCP OPERATOR SURFACE
-> M5 PROVIDER GATEWAY + ISOLATED WORKERS
-> M6 GENERATOR-EVALUATOR REPAIR LOOP
-> M7 30-60 SECOND CONTROLLED PROOF
```

## Rejected architecture

A single autonomous director agent carrying the whole screenplay in context and generating scenes sequentially is prohibited.

That design recreates the exact failures Continuity Forge exists to prevent:

- Context loss
- Visual drift
- Narrative compression
- Non-reproducible decisions
- Weak provenance
- Uncontrolled revision cascades

## Canonical rule

> Models generate pixels and proposals. Continuity Forge governs identity, memory, causality, approvals, and production truth.
