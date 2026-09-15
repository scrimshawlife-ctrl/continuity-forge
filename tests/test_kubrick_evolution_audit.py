"""Regression coverage for embedded and packaged Kubrick evidence evolution."""

import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from yaml import YAMLError

ROOT = Path(__file__).resolve().parents[1]
ENGINES = [
    ROOT / "skills/kubrick/scripts/evolve_from_use.py",
    ROOT / "packages/kubrick_helpers/src/kubrick_helpers/evolution.py",
]


@pytest.fixture(params=ENGINES, ids=["embedded", "package"])
def engine(request):
    spec = importlib.util.spec_from_file_location("evolution_audit", request.param)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repeated_evidence_does_not_inflate_confidence(engine):
    info = {"data": {"pattern_id": "p", "confidence": 0.7}}
    usage = {
        "p": {
            "uses": 3,
            "total_score": 2.4,
            "success_signals": 1,
            "failure_signals": 0,
            "projects": ["film"],
        }
    }
    first = engine.evolve_sidecar(info, usage)
    info["data"] = first
    before = json.dumps(first, sort_keys=True)
    assert engine.evolve_sidecar(info, usage) is None
    assert json.dumps(info["data"], sort_keys=True) == before


def tree(root):
    return {
        str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


def corpus(root):
    for name in ("patterns", "receipts", "outcomes"):
        (root / name).mkdir()
    (root / "patterns/p.json").write_text(
        json.dumps(
            {
                "pattern_id": "p",
                "confidence": 0.7,
                "title": "Test pattern",
                "domain": "cinematic",
                "source_tier": "PRIMARY",
                "dramatic_operations": [],
                "cinematic_affordances": [],
            }
        )
    )
    for i in range(3):
        (root / f"receipts/{i}.json").write_text(
            json.dumps(
                {
                    "request_hash": str(i),
                    "ranked_patterns": [{"pattern_id": "p", "total_score": 0.8}],
                }
            )
        )
    (root / "outcomes/ok.json").write_text(
        json.dumps({"pattern_id": "p", "outcome": "success", "project": "film"})
    )
    (root / "index.yaml").write_text(
        "by_dramatic_problem:\n  test:\n    patterns: [unused, p, missing]\n"
    )


def test_cli_dry_run_is_zero_write(engine, tmp_path):
    import subprocess
    import sys

    corpus(tmp_path)
    before = tree(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            engine.__file__,
            "--receipts-dir",
            str(tmp_path / "receipts"),
            "--outcomes-dir",
            str(tmp_path / "outcomes"),
            "--patterns-dir",
            str(tmp_path / "patterns"),
            "--index",
            str(tmp_path / "index.yaml"),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["evolution_receipt"]["dry_run"] is True
    assert tree(tmp_path) == before


def test_duplicate_files_and_overlapping_windows_are_consumed_once(engine, tmp_path):
    corpus(tmp_path)
    usage = engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")
    info = {"data": {"pattern_id": "p", "confidence": 0.7}}
    first = engine.evolve_sidecar(info, usage)
    info["data"] = first
    (tmp_path / "receipts/copy.json").write_bytes((tmp_path / "receipts/0.json").read_bytes())
    duplicated = engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")
    assert duplicated == usage
    (tmp_path / "outcomes/new.json").write_text(
        json.dumps({"pattern_id": "p", "outcome": "failure", "project": "other"})
    )
    second = engine.evolve_sidecar(
        info, engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")
    )
    assert second["confidence"] == 0.73  # baseline .7 + retrieval .03, balanced outcomes
    assert engine.evolve_sidecar({"data": second}, usage) is None  # old subset is not new evidence


def test_apply_has_unique_receipt_and_repeat_is_noop(engine, tmp_path):
    corpus(tmp_path)
    kwargs = {
        "receipts_dir": tmp_path / "receipts",
        "outcomes_dir": tmp_path / "outcomes",
        "patterns_dir": tmp_path / "patterns",
        "index_path": tmp_path / "index.yaml",
        "dry_run": False,
    }
    result = engine.run_evolution(**kwargs)["evolution_receipt"]
    assert Path(result["receipt_path"]).is_file()
    before = tree(tmp_path)
    assert engine.run_evolution(**kwargs)["evolution_receipt"]["patterns_evolved"] == []
    assert tree(tmp_path) == before


def test_invalid_index_prevents_partial_apply(engine, tmp_path):
    corpus(tmp_path)
    (tmp_path / "index.yaml").write_text("by_dramatic_problem: [")
    before = tree(tmp_path)
    with pytest.raises((YAMLError, ValidationError)):
        engine.run_evolution(
            tmp_path / "receipts",
            tmp_path / "outcomes",
            tmp_path / "patterns",
            tmp_path / "index.yaml",
            dry_run=False,
        )
    assert tree(tmp_path) == before


def test_same_identity_changed_evidence_is_rejected(engine, tmp_path):
    corpus(tmp_path)
    usage = engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")
    evolved = engine.evolve_sidecar({"data": {"pattern_id": "p", "confidence": 0.7}}, usage)
    path = tmp_path / "receipts/0.json"
    rec = json.loads(path.read_text())
    rec["ranked_patterns"][0]["total_score"] = 0.4
    path.write_text(json.dumps(rec))
    with pytest.raises(ValueError, match="conflicting"):
        engine.evolve_sidecar(
            {"data": evolved}, engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")
        )


@pytest.mark.parametrize("recipients", [[{"pattern_id": "q", "total_score": 0.8}], []])
def test_consumed_identity_cannot_move_to_disjoint_patterns(engine, tmp_path, recipients):
    corpus(tmp_path)
    q = json.loads((tmp_path / "patterns/p.json").read_text())
    q["pattern_id"] = "q"
    (tmp_path / "patterns/q.json").write_text(json.dumps(q))
    args = (tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns")
    engine.run_evolution(*args, dry_run=False)
    path = tmp_path / "receipts/0.json"
    record = json.loads(path.read_text())
    record["ranked_patterns"] = recipients
    path.write_text(json.dumps(record))
    before = tree(tmp_path)
    with pytest.raises(ValueError, match="conflicting.*stable identity"):
        engine.run_evolution(*args, dry_run=False)
    assert tree(tmp_path) == before
    assert not (tmp_path / "patterns/.evolution.lock").exists()


def test_timestamp_change_is_not_new_evidence(engine, tmp_path):
    corpus(tmp_path)
    usage = engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")
    path = tmp_path / "receipts/0.json"
    rec = json.loads(path.read_text())
    rec["timestamp"] = "new timestamp"
    path.write_text(json.dumps(rec))
    assert engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes") == usage


def test_unknown_pattern_fails_closed(engine, tmp_path):
    corpus(tmp_path)
    (tmp_path / "patterns/p.json").unlink()
    with pytest.raises(ValueError, match="unknown pattern"):
        engine.run_evolution(tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns")


def test_schema_invalid_sidecar_is_rejected_before_apply(engine, tmp_path):
    corpus(tmp_path)
    path = tmp_path / "patterns/p.json"
    data = json.loads(path.read_text())
    data["title"] = 42
    path.write_text(json.dumps(data))
    before = tree(tmp_path)
    with pytest.raises((YAMLError, ValidationError)):
        engine.run_evolution(
            tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns", dry_run=False
        )
    assert tree(tmp_path) == before


@pytest.mark.parametrize(
    "bad", ["{", '{"request_hash":"bad","ranked_patterns":[{"pattern_id":"p","total_score":NaN}]}']
)
def test_malformed_evidence_prevents_all_writes(engine, tmp_path, bad):
    corpus(tmp_path)
    (tmp_path / "receipts/bad.json").write_text(bad)
    before = tree(tmp_path)
    with pytest.raises((ValueError, TypeError)):
        engine.run_evolution(
            tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns", dry_run=False
        )
    assert tree(tmp_path) == before


def test_changed_consumed_outcome_is_conflict(engine, tmp_path):
    corpus(tmp_path)
    first = engine.evolve_sidecar(
        {"data": {"pattern_id": "p", "confidence": 0.7}},
        engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes"),
    )
    path = tmp_path / "outcomes/ok.json"
    data = json.loads(path.read_text())
    data["outcome"] = "failure"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="conflicting"):
        engine.evolve_sidecar(
            {"data": first}, engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")
        )


def test_caught_replace_failure_rolls_back_every_file(engine, tmp_path, monkeypatch):
    corpus(tmp_path)
    q = json.loads((tmp_path / "patterns/p.json").read_text())
    q["pattern_id"] = "q"
    (tmp_path / "patterns/q.json").write_text(json.dumps(q))
    (tmp_path / "receipts/q.json").write_text(
        json.dumps(
            {"request_hash": "q", "ranked_patterns": [{"pattern_id": "q", "total_score": 0.8}]}
        )
    )
    before = {p: value[0] for p, value in tree(tmp_path).items()}
    replace = engine.os.replace
    calls = 0

    def fail_third(source, target):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected replacement failure")
        return replace(source, target)

    monkeypatch.setattr(engine.os, "replace", fail_third)
    with pytest.raises(OSError, match="injected"):
        engine.run_evolution(
            tmp_path / "receipts",
            tmp_path / "outcomes",
            tmp_path / "patterns",
            tmp_path / "index.yaml",
            dry_run=False,
        )
    assert {p: value[0] for p, value in tree(tmp_path).items()} == before
    assert not (tmp_path / "patterns/.evolution.lock").exists()


@pytest.mark.parametrize("pattern_count", [2, 3])
def test_double_fault_retains_recovery_guard_and_attempts_all_restores(
    engine, tmp_path, monkeypatch, pattern_count
):
    corpus(tmp_path)
    template = json.loads((tmp_path / "patterns/p.json").read_text())
    for pid in ["q", "r"][: pattern_count - 1]:
        (tmp_path / f"patterns/{pid}.json").write_text(json.dumps(dict(template, pattern_id=pid)))
        (tmp_path / f"receipts/{pid}.json").write_text(
            json.dumps(
                {
                    "request_hash": pid,
                    "ranked_patterns": [{"pattern_id": pid, "total_score": 0.8}],
                }
            )
        )
    before = {p: p.read_bytes() for p in (tmp_path / "patterns").glob("*.json")}
    replace = engine.os.replace
    targets = []

    def double_fault(source, target):
        targets.append(Path(target))
        if len(targets) == pattern_count + 1:
            raise OSError("injected apply failure")
        if len(targets) == pattern_count + 2:
            raise OSError("injected restore failure")
        return replace(source, target)

    monkeypatch.setattr(engine.os, "replace", double_fault)
    with pytest.raises(Exception) as caught:
        engine.run_evolution(
            tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns", dry_run=False
        )
    message = str(caught.value)
    assert "injected apply failure" in message
    assert "injected restore failure" in message
    receipt_path = targets[0]
    assert str(receipt_path) in message
    assert receipt_path.is_file()
    lock = tmp_path / "patterns/.evolution.lock"
    assert lock.is_dir()
    receipt = json.loads(receipt_path.read_text())["evolution_receipt"]
    assert receipt["before_contents"] == {str(p): b.decode() for p, b in before.items()}
    activated = targets[1:pattern_count]
    assert targets[pattern_count + 1 :] == list(reversed(activated))
    failed_restore = activated[-1]
    for path, contents in before.items():
        assert (path.read_bytes() == contents) == (path != failed_restore)
    assert set((tmp_path / "patterns").iterdir()) == set(before) | {lock}
    with pytest.raises(FileExistsError):
        engine.run_evolution(
            tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns", dry_run=False
        )


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX mode contract")
@pytest.mark.parametrize("rollback", [False, True])
def test_evolution_preserves_staged_and_rollback_modes(engine, tmp_path, monkeypatch, rollback):
    import stat

    corpus(tmp_path)
    q = json.loads((tmp_path / "patterns/p.json").read_text())
    q["pattern_id"] = "q"
    (tmp_path / "patterns/q.json").write_text(json.dumps(q))
    (tmp_path / "receipts/q.json").write_text(
        json.dumps(
            {"request_hash": "q", "ranked_patterns": [{"pattern_id": "q", "total_score": 0.1}]}
        )
    )
    (tmp_path / "index.yaml").write_text("by_dramatic_problem:\n  test:\n    patterns: [q, p]\n")
    paths = [tmp_path / "patterns/p.json", tmp_path / "index.yaml"]
    modes = dict(zip(paths, [0o640, 0o664], strict=True))
    for path, mode in modes.items():
        path.chmod(mode)
    before = {path: path.read_bytes() for path in paths}
    replace = engine.os.replace
    installed = []

    def inspect_replace(source, target):
        if target in modes:
            assert stat.S_IMODE(Path(source).stat().st_mode) == modes[target]
            installed.append(target)
        return replace(source, target)

    monkeypatch.setattr(engine.os, "replace", inspect_replace)
    read_bytes = Path.read_bytes
    failed = False

    def fail_verification(path):
        nonlocal failed
        if rollback and len(installed) == 2 and not failed and path == paths[0]:
            failed = True
            raise OSError("injected read-back failure")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_verification)
    args = (tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns", paths[1])
    if rollback:
        with pytest.raises(OSError, match="injected read-back"):
            engine.run_evolution(*args, dry_run=False)
        assert {path: path.read_bytes() for path in paths} == before
        assert installed == paths + list(reversed(paths))
    else:
        engine.run_evolution(*args, dry_run=False)
        assert installed == paths
    assert {path: stat.S_IMODE(path.stat().st_mode) for path in paths} == modes


def test_embedded_package_code_and_schema_parity():
    assert ENGINES[0].read_bytes() == ENGINES[1].read_bytes()
    assert (
        ROOT / "skills/kubrick/schemas/symbolic-narrative-pattern.schema.json"
    ).read_bytes() == ENGINES[1].with_name("symbolic-narrative-pattern.schema.json").read_bytes()


@pytest.mark.parametrize("score", [True, "0.8"])
def test_scores_do_not_coerce_invalid_types(engine, tmp_path, score):
    corpus(tmp_path)
    (tmp_path / "receipts/0.json").write_text(
        json.dumps(
            {"request_hash": "0", "ranked_patterns": [{"pattern_id": "p", "total_score": score}]}
        )
    )
    with pytest.raises(ValueError):
        engine.aggregate_usage(tmp_path / "receipts", tmp_path / "outcomes")


def test_sidecar_symlink_cannot_escape_write_root(engine, tmp_path):
    corpus(tmp_path)
    outside = tmp_path / "outside.json"
    path = tmp_path / "patterns/p.json"
    path.rename(outside)
    path.symlink_to(outside)
    before = tree(tmp_path)
    with pytest.raises(ValueError, match="symlink"):
        engine.run_evolution(
            tmp_path / "receipts", tmp_path / "outcomes", tmp_path / "patterns", dry_run=False
        )
    assert tree(tmp_path) == before


def test_reviewed_plan_rejects_changed_evidence(engine, tmp_path):
    corpus(tmp_path)
    args = (
        tmp_path / "receipts",
        tmp_path / "outcomes",
        tmp_path / "patterns",
        tmp_path / "index.yaml",
    )
    plan = engine.run_evolution(*args)["evolution_receipt"]
    assert "plan_hash" in plan
    (tmp_path / "receipts/0.json").write_text(
        json.dumps(
            {"request_hash": "new", "ranked_patterns": [{"pattern_id": "p", "total_score": 0.8}]}
        )
    )
    before = tree(tmp_path)
    with pytest.raises(ValueError, match="stale"):
        engine.run_evolution(*args, dry_run=False, expected_plan_hash=plan["plan_hash"])
    assert tree(tmp_path) == before


def test_retrieval_does_not_log_to_installed_skill_by_default(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "retrieval_audit", ROOT / "skills/kubrick/scripts/retrieve_symbolic_patterns.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "SKILL_ROOT", str(tmp_path))
    module.run_retrieval({"dramatic_problem": "identity"})
    assert not list(tmp_path.iterdir())


def test_index_preserves_unused_and_missing_sidecar_entries(engine, tmp_path):
    import yaml

    index = tmp_path / "index.yaml"
    index.write_text("by_dramatic_problem:\n  test:\n    patterns: [unused, p, missing]\n")
    engine.update_index_from_usage(
        str(index), {"p": {"success_signals": 1}}, {"p": {"data": {"confidence": 0.8}}}
    )
    assert sorted(yaml.safe_load(index.read_text())["by_dramatic_problem"]["test"]["patterns"]) == [
        "missing",
        "p",
        "unused",
    ]
