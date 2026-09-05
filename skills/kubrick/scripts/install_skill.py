#!/usr/bin/env python3
"""Install only this embedded skill, with target-scoped backups outside discovery."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("category", nargs="?", choices=["creative", "categorized"])
    parser.add_argument("--target", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only (default)")
    mode.add_argument("--apply", action="store_true", help="Install after reviewing target")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).resolve()
    target = (
        args.target or home / "skills" / ("creative/kubrick" if args.category else "kubrick")
    ).resolve()
    if target == source or target in source.parents or source in target.parents:
        parser.error("source and target must not overlap")
    if target.exists() and not target.is_dir():
        parser.error("target must be a directory")
    key = hashlib.sha256(str(target).encode()).hexdigest()[:20]
    backup_root = home / "receipts/kubrick-backups" / key
    if target == backup_root or target in backup_root.parents or backup_root in target.parents:
        parser.error("target and backup root must not overlap")
    # Fail before creating any directories if source integrity is broken.
    for required in ("SKILL.md", "references/corpus-index.yaml", "scripts/evolve_from_use.py"):
        if not (source / required).is_file():
            parser.error(f"missing skill source: {required}")
    for path in (source / "scripts").glob("*.py"):
        compile(path.read_text(), str(path), "exec")  # syntax validation, no execution
    plan = {
        "source": str(source),
        "target": str(target),
        "backup_root": str(backup_root),
        "dry_run": not args.apply,
        "source_variant": "scrimshawlife-ctrl/continuity-forge:skills/kubrick",
    }
    if not args.apply:
        print(json.dumps(plan))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".kubrick-stage-", dir=target.parent))
    backup = None
    activated = False
    backup_complete = False
    try:
        shutil.copytree(
            source,
            stage,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
        )
        for required in ("SKILL.md", "references/corpus-index.yaml", "scripts/evolve_from_use.py"):
            if (stage / required).read_bytes() != (source / required).read_bytes():
                raise OSError(f"staging verification failed: {required}")
        if target.exists():
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_root / uuid.uuid4().hex
            # Copy backup first: the old install remains intact if copying fails.
            shutil.copytree(target, backup)
            backup_complete = True
            shutil.rmtree(target)
        os.replace(stage, target)
        activated = True
        if (target / "SKILL.md").read_bytes() != (source / "SKILL.md").read_bytes():
            raise OSError("installed skill verification failed")
    except Exception:
        if backup_complete and backup is not None and backup.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(backup, target)
        elif activated:
            shutil.rmtree(target)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    plan.update(installed=True, backup=str(backup) if backup else None)
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
