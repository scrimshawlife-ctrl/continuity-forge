# Evolution and installation safety

## Source ownership

This is the **embedded continuity-forge Kubrick variant**, maintained with
scrimshawlife-ctrl/continuity-forge. It is not interchangeable with standalone
personal or Zero-State-LLC/Kubrick releases. Record `git rev-parse HEAD` from the
chosen checkout before installation. Keep only one `kubrick` trigger installed in
the intended profile. Migrating variants requires an explicit human choice and
backup of project data; do not merge histories or infer license changes.
Scriptwriting remains a compatibility procedural variant; prefer Kubrick for new
symbolic work, but do not silently replace an existing scriptwriting installation.

## Installation

Resolve the absolute skill directory (from skill_view or checkout), not caller cwd.
Use `terminal(command='bash skills/kubrick/install.sh --dry-run')` from repo root;
review source, target and backup root, then the same command with `--apply`.
The installer resolves `${HERMES_HOME:-$HOME/.hermes}`, supports `--target`, stages
only this skill and keeps unique target-keyed backups outside skill discovery.
Windows without Bash: use `python skills/kubrick/scripts/install_skill.py --dry-run`.
The installer validates syntax/content, not creative quality. To restore, stop
users of the target, review the exact reported backup and copy it back to that
same target; never choose a backup from a different target hash. Keep old backups.

## Evolution prerequisites

Creative use needs no package. Evolution requires Python 3.12+, PyYAML and jsonschema:
`terminal(command="python -m pip install pyyaml jsonschema")` in a reviewed venv;
or full-checkout `python -m pip install -e '.[kubrick-helpers]'`.
Embedded script and packaged `kubrick-evolve` share tested behavior and schema.
Do not write usage into an installed skill. Copy `references/patterns/` and
`references/corpus-index.yaml` to a project-owned corpus and create separate
receipts/outcomes directories with write_file or approved filesystem tools.

Use `terminal(command='python skills/kubrick/scripts/evolve_from_use.py --receipts-dir PROJECT/receipts --outcomes-dir PROJECT/outcomes --patterns-dir PROJECT/patterns --index PROJECT/corpus-index.yaml --dry-run')`.
Replace PROJECT with the actual reviewed absolute project directory. Dry-run and
omitted mode both create **zero files** (including no receipts/locks). Review the
JSON change list and hashes; replace `--dry-run` with
`--apply --expected-plan-hash REVIEWED_HASH` (the returned plan_hash) to mutate that
explicit corpus. The packaged `kubrick-evolve` accepts exactly the same arguments.

## Evidence contract

Persist real retrieval output explicitly at a project path; don't invent successes.
The embedded retrieval helper defaults to no logging; opt in with `--log-dir PROJECT/receipts`.
Retrieval JSON/YAML contains `retrieval_receipt` or the unwrapped record, with
`request_hash` (or `event_id`) and `ranked_patterns` (top three consumed).
Each item has `pattern_id` and finite numeric `total_score` in [0,1].
Outcomes have `pattern_id`, `project`, `outcome` (success, failure, debt, collision,
revision_broken, neutral), and preferably immutable `event_id`.
Without event_id an outcome identity is project+pattern: corrections conflict,
not fresh evidence. Renames, copies, timestamp and metadata changes do not count
again. A stable identity with altered scored contents is rejected, even after
prior consumption. Do not mint a new ID to disguise a correction; review/rebuild
from the original baseline with a curated evidence set instead.

Late outcomes recompute confidence from a fixed baseline plus all consumed events,
not from already-adjusted confidence. Identical/subset evidence is a no-op;
no new history/version or receipt is written. Legacy aggregate-only Python callers
get exact-window dedupe only; use file evidence for overlapping windows.
Pre-upgrade histories cannot prove consumed event IDs: restore a reviewed pristine
corpus and replay curated evidence once, rather than using already-inflated legacy
confidence as a baseline. Unknown patterns, invalid schema/JSON/YAML or nonfinite
numbers stop the operation, not partial success.

## Apply / recovery / verification

Apply uses a single-corpus lock, validates and stages all changed sidecars/index,
then replaces individual files atomically with rollback for caught failures.
It is **not crash-atomic across files**. A unique evolution-UUID.json beside the
patterns directory is persisted before corpus replacement and includes prior
contents and before/after hashes. Its existence alone is not success: compare all
after hashes with current files. A process/host crash may leave partial application
and a stale lock; stop writers, inspect the receipt, restore all before contents
or finish a reviewed recovery, then remove the stale lock. Do not auto-clear it.

Only confidence, history, evolution event/baseline state, version, timestamp and
index ordering change; no new patterns or structural edits are inferred. Read-back
must match the planned hashes. Run the identical apply again: no files or mtimes
should change. Regression command from checkout:
`terminal(command="python -m pytest tests/test_kubrick_evolution_audit.py tests/test_kubrick_install_audit.py -q")`.
