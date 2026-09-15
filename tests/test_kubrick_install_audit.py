"""Installer exercises run only in isolated HOME/profile directories."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "skills/kubrick/install.sh"


def install(tmp_path, *args):
    env = dict(os.environ, HOME=str(tmp_path / "home"), HERMES_HOME=str(tmp_path / "profile"))
    return subprocess.run(
        ["bash", str(INSTALLER), *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_install_plan_is_zero_write_and_profile_aware(tmp_path):
    result = install(tmp_path, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())
    plan = json.loads(result.stdout)
    assert plan["target"] == str(tmp_path / "profile/skills/kubrick")
    assert plan["source"] == str(ROOT / "skills/kubrick")


def test_install_from_unrelated_cwd_preserves_unique_backups(tmp_path):
    result = install(tmp_path, "--apply")
    assert result.returncode == 0, result.stderr
    target = tmp_path / "profile/skills/kubrick"
    assert (target / "SKILL.md").is_file()
    assert not (tmp_path / "home/.hermes").exists()
    (target / "sentinel").write_text("user data")
    assert install(tmp_path, "--apply").returncode == 0
    backups = list((tmp_path / "profile/receipts/kubrick-backups").rglob("sentinel"))
    assert len(backups) == 1
    assert backups[0].read_text() == "user data"
    assert not list((tmp_path / "profile/skills").glob("*.bak*"))
    assert install(tmp_path, "--apply").returncode == 0
    assert backups[0].read_text() == "user data"


def test_install_rejects_profile_root_before_writes(tmp_path):
    result = install(tmp_path, "--target", str(tmp_path / "profile"), "--dry-run")
    assert result.returncode != 0
    assert not list(tmp_path.iterdir())


def test_failed_backup_copy_does_not_replace_existing_install(tmp_path, monkeypatch):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "install_audit", INSTALLER.parent / "scripts/install_skill.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    profile = tmp_path / "profile"
    target = profile / "skills/kubrick"
    target.mkdir(parents=True)
    (target / "sentinel").write_text("keep")
    monkeypatch.setenv("HERMES_HOME", str(profile))
    monkeypatch.setattr(sys, "argv", ["installer", "--apply"])
    copytree = module.shutil.copytree

    def failing_copy(source, destination, *args, **kwargs):
        if Path(source) == target:
            Path(destination).mkdir(parents=True)
            raise OSError("backup interrupted")
        return copytree(source, destination, *args, **kwargs)

    monkeypatch.setattr(module.shutil, "copytree", failing_copy)
    import pytest

    with pytest.raises(OSError, match="backup interrupted"):
        module.main()
    assert (target / "sentinel").read_text() == "keep"


def test_install_refuses_source_ancestry(tmp_path):
    result = install(tmp_path, "--target", str(ROOT / "skills"), "--dry-run")
    assert result.returncode != 0
