"""
Tooling tests for realitycheck.runner.

Covers:
    - sha256_file produces a stable digest
    - create_protected_manifest / verify_protected_manifest:
        * unchanged file verifies OK
        * changed file is detected
        * missing file is detected
    - snapshot_application changes when a file changes
    - run_pytest:
        * passing test suite → outcome == "passed"
        * failing test suite → outcome == "failed"
        * artifacts (stdout.txt, stderr.txt, junit.xml, execution.json) are created
"""

import json
import os
import textwrap
from pathlib import Path

import pytest

from realitycheck.runner import (
    create_protected_manifest,
    run_pytest,
    sha256_file,
    snapshot_application,
    verify_protected_manifest,
)


# ---------------------------------------------------------------------------
# sha256_file
# ---------------------------------------------------------------------------


def test_sha256_file_stable(tmp_path):
    f = tmp_path / "data.txt"
    f.write_bytes(b"hello world")
    d1 = sha256_file(f)
    d2 = sha256_file(f)
    assert d1 == d2
    assert len(d1) == 64  # hex sha256


def test_sha256_file_changes_with_content(tmp_path):
    f = tmp_path / "data.txt"
    f.write_bytes(b"hello world")
    d1 = sha256_file(f)
    f.write_bytes(b"goodbye world")
    d2 = sha256_file(f)
    assert d1 != d2


# ---------------------------------------------------------------------------
# Protected manifest — happy path
# ---------------------------------------------------------------------------


def test_protected_manifest_unchanged_verifies_ok(tmp_path):
    (tmp_path / "a.txt").write_text("content a")
    (tmp_path / "b.txt").write_text("content b")
    manifest_path = tmp_path / "protected.json"
    create_protected_manifest(tmp_path, ["a.txt", "b.txt"], manifest_path)
    result = verify_protected_manifest(tmp_path, manifest_path)
    assert result["ok"] is True
    assert result["missing"] == []
    assert result["modified"] == []


# ---------------------------------------------------------------------------
# Protected manifest — modified file detected
# ---------------------------------------------------------------------------


def test_protected_manifest_detects_modified_file(tmp_path):
    f = tmp_path / "contract.md"
    f.write_text("original content")
    manifest_path = tmp_path / "protected.json"
    create_protected_manifest(tmp_path, ["contract.md"], manifest_path)

    # Modify the file after creating the manifest
    f.write_text("tampered content")

    result = verify_protected_manifest(tmp_path, manifest_path)
    assert result["ok"] is False
    assert "contract.md" in result["modified"]
    assert result["missing"] == []


# ---------------------------------------------------------------------------
# Protected manifest — missing file detected
# ---------------------------------------------------------------------------


def test_protected_manifest_detects_missing_file(tmp_path):
    f = tmp_path / "fixture.jsonl"
    f.write_text('{"id": 1}')
    manifest_path = tmp_path / "protected.json"
    create_protected_manifest(tmp_path, ["fixture.jsonl"], manifest_path)

    # Remove the file after creating the manifest
    f.unlink()

    result = verify_protected_manifest(tmp_path, manifest_path)
    assert result["ok"] is False
    assert "fixture.jsonl" in result["missing"]
    assert result["modified"] == []


# ---------------------------------------------------------------------------
# Application snapshot
# ---------------------------------------------------------------------------


def test_snapshot_changes_when_file_changes(tmp_path):
    app_dir = tmp_path / "myapp"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "logic.py").write_text("def f(): return 1\n")

    snap1 = snapshot_application(app_dir)

    # Modify logic.py
    (app_dir / "logic.py").write_text("def f(): return 2\n")
    snap2 = snapshot_application(app_dir)

    assert snap1["snapshot_id"] != snap2["snapshot_id"]


def test_snapshot_stable_when_unchanged(tmp_path):
    app_dir = tmp_path / "myapp"
    app_dir.mkdir()
    (app_dir / "logic.py").write_text("def f(): pass\n")

    snap1 = snapshot_application(app_dir)
    snap2 = snapshot_application(app_dir)
    assert snap1["snapshot_id"] == snap2["snapshot_id"]


# ---------------------------------------------------------------------------
# run_pytest — passing test
# ---------------------------------------------------------------------------


def _write_passing_test(directory: Path, filename: str = "test_pass.py") -> Path:
    p = directory / filename
    p.write_text(
        textwrap.dedent(
            """\
            def test_always_passes():
                assert 1 + 1 == 2
            """
        )
    )
    return p


def _write_failing_test(directory: Path, filename: str = "test_fail.py") -> Path:
    p = directory / filename
    p.write_text(
        textwrap.dedent(
            """\
            def test_always_fails():
                assert 1 == 2, "intentional failure"
            """
        )
    )
    return p


@pytest.fixture
def run_workspace(tmp_path):
    """A minimal workspace containing only a sample_app stub (for snapshot)."""
    app_dir = tmp_path / "sample_app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    return tmp_path


def test_runner_passing_test(run_workspace, tmp_path):
    test_dir = run_workspace / "tests_tmp"
    test_dir.mkdir()
    _write_passing_test(test_dir)

    execution = run_pytest(
        repo_root=run_workspace,
        pytest_targets=[str(test_dir)],
        run_id="test-run-pass",
        phase="independent",
    )

    assert execution["outcome"] == "passed"
    assert execution["exit_code"] == 0


def test_runner_failing_test(run_workspace):
    test_dir = run_workspace / "tests_tmp"
    test_dir.mkdir()
    _write_failing_test(test_dir)

    execution = run_pytest(
        repo_root=run_workspace,
        pytest_targets=[str(test_dir)],
        run_id="test-run-fail",
        phase="independent",
    )

    assert execution["outcome"] == "failed"
    assert execution["exit_code"] == 1


def test_runner_artifacts_are_created(run_workspace):
    test_dir = run_workspace / "tests_tmp"
    test_dir.mkdir()
    _write_passing_test(test_dir)

    execution = run_pytest(
        repo_root=run_workspace,
        pytest_targets=[str(test_dir)],
        run_id="test-run-artifacts",
        phase="independent",
        execution_id="exec-001",
    )

    exec_dir = run_workspace / "runs" / "test-run-artifacts" / "exec-001"
    assert (exec_dir / "stdout.txt").exists()
    assert (exec_dir / "stderr.txt").exists()
    assert (exec_dir / "junit.xml").exists()
    assert (exec_dir / "execution.json").exists()
    assert (exec_dir / "application-snapshot.json").exists()
    assert (exec_dir / "environment.json").exists()

    rec = json.loads((exec_dir / "execution.json").read_text())
    assert rec["execution_id"] == "exec-001"
    assert rec["phase"] == "independent"
    assert isinstance(rec["duration_ms"], int)


# ---------------------------------------------------------------------------
# compute_verdict
# ---------------------------------------------------------------------------


from realitycheck.runner import compute_verdict


def _make_exec(outcome: str, phase: str = "verification") -> dict:
    return {
        "execution_id": "x",
        "phase": phase,
        "outcome": outcome,
        "exit_code": 0 if outcome == "passed" else 1,
        "duration_ms": 10,
        "started_at": "2025-01-01T00:00:00+00:00",
        "pytest_targets": ["tests/regression"],
        "application_snapshot": "abc123",
        "protected_manifest": None,
        "structured_results": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "cases": []},
    }


def test_verdict_verified(tmp_path):
    repro = _make_exec("failed", "reproduction")
    verif = _make_exec("passed", "verification")
    v = compute_verdict(repro, verif, {"ok": True, "missing": [], "modified": []})
    assert v["status"] == "verified_for_tested_scenarios"


def test_verdict_repair_failed(tmp_path):
    repro = _make_exec("failed", "reproduction")
    verif = _make_exec("failed", "verification")
    v = compute_verdict(repro, verif, {"ok": True, "missing": [], "modified": []})
    assert v["status"] == "repair_failed"


def test_verdict_blocked_protected_manifest(tmp_path):
    repro = _make_exec("failed", "reproduction")
    verif = _make_exec("passed", "verification")
    v = compute_verdict(repro, verif, {"ok": False, "missing": ["contract.md"], "modified": []})
    assert v["status"] == "blocked"


def test_verdict_blocked_timeout(tmp_path):
    repro = _make_exec("failed", "reproduction")
    verif = _make_exec("timeout", "verification")
    v = compute_verdict(repro, verif, {"ok": True, "missing": [], "modified": []})
    assert v["status"] == "blocked"


def test_verdict_blocked_no_tests_collected(tmp_path):
    repro = _make_exec("failed", "reproduction")
    verif = {**_make_exec("passed", "verification"), "structured_results": {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "cases": []}}
    v = compute_verdict(repro, verif, {"ok": True, "missing": [], "modified": []})
    assert v["status"] == "blocked"
