# Kubrick — embedded Continuity Forge variant

Creative narrative work is standalone. Load SKILL.md and
[standalone-procedure](references/standalone-procedure.md); Forge is optional for
explicit canon handoff, not a prerequisite to write or diagnose a scene.

## Install safely

From the continuity-forge checkout, record `git rev-parse HEAD`, then:

```bash
bash skills/kubrick/install.sh --dry-run
# Review active-profile target and backup root before opting in:
bash skills/kubrick/install.sh --apply
```

`HERMES_HOME` selects the profile. `--target` selects an explicit destination;
`creative` selects categorized installation. From another cwd, use the absolute
installer path, never `cp -R .`. Python-only Windows hosts can invoke
`scripts/install_skill.py`. This installs the skill directory, not a package.
See [source ownership, backups and evolution safety](references/evolution-safety.md).
Do not install this variant alongside another `kubrick` trigger or assume personal,
organizational and embedded releases are identical. No license is changed here.

## Optional Python helpers

The continuity-forge wheel includes kubrick_helpers and its CLIs, **not** SKILL.md
or the narrative corpus. Python 3.12+ editable install from repo root:
`python -m pip install -e '.[kubrick-helpers]'`.
The standalone evolution script requires `pyyaml` and `jsonschema` in a reviewed
venv. Creative use needs neither. Retrieval emits candidate ranking receipts;
persist real receipts explicitly in project-owned directories.

## Evolution

No unattended auto-evolution is enabled. Copy the pattern corpus/index to a
project directory and use the complete plan/apply recipe in
[references/evolution-safety.md](references/evolution-safety.md).
Default mode and `--dry-run` are zero-write. `--apply` validates changed sidecars,
deduplicates immutable evidence, recomputes cumulative scores from a fixed
baseline, preserves unused index entries, and writes a unique recovery receipt.
Caught I/O failures roll back; multi-file changes are not crash-atomic.

## Forge handoff

Use [the MCP handoff recipe](references/continuity-forge-integration.md).
There is no Forge ingest CLI. Symbolic packets remain proposed attachments unless
the actual kernel schema and returned persisted state demonstrate support.

## Verification

From a Python 3.12+ checkout with `.[dev,kubrick-helpers]`:
`python -m pytest tests/test_kubrick_evolution_audit.py tests/test_kubrick_install_audit.py tests/test_authored_skill_recipes.py tests/test_kubrick_esoteric.py -q`.
All installer/evolution writes use disposable directories; recipe tests use a
fresh local runtime and mock provider, not live services.
