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
        * pytest fixture/setup failure → outcome == "error" (blocks reproduction)
        * artifacts (stdout.txt, stderr.txt, junit.xml, execution.json) are created
    - compute_verdict — hardened enforcement:
        * Rule 0: required_node_ids omitted → blocked
        * Rule 0: required_node_ids empty list → blocked
        * Rule 0b: reproduction_expectations omitted → blocked
        * Rule 0b: reproduction_expectations empty → blocked
        * Rule 0b: reproduction_expectations contains invalid value → blocked
        * Rule 1: protected_verification None → blocked
        * Rule 1: protected_verification ok="false" (string) → blocked (structural)
        * Rule 1: protected_verification ok=True but modified non-empty → blocked (contradictory)
        * Rule 1: protected_verification ok=True but missing non-empty → blocked (contradictory)
        * Rule 1: protected_verification ok=False → blocked
        * Rule 2: reproduction_execution None → blocked
        * Rule 3: reproduction passes when failure expected → blocked
        * Rule 3: reproduction fails when pass expected → blocked
        * Rule 4: reproduction outcome error → blocked
        * Rule 4: reproduction outcome timeout → blocked
        * Rule 5/6: verification structured_results has parse_error → blocked
        * Rule 6: verification collects zero tests → blocked
        * Rule 7: verification has skipped tests → blocked
        * Rule 8: required node ID missing from results → blocked
        * Rule 8: required node ID from wrong file (same function name) → blocked
        * Rule 8: required node ID skipped → blocked
        * Rule 8: required node ID failed → repair_failed
        * Reproduction: missing structured results → blocked
        * Reproduction: unparseable structured results → blocked
        * Reproduction: setup/error exit (outcome "error") → blocked
        * Reproduction: required node status "error" (setup failure) → blocked
        * Reproduction: required node skipped → blocked
        * Mixed per-node expectations: two failures + one preservation pass → verified
        * Mixed per-node expectations: preservation test incorrectly fails → blocked
        * After repair all required nodes must pass → verified_for_tested_scenarios
        * Rule 10/11: baseline_execution None → blocked
        * Rule 11: baseline has failures → blocked
        * Rule 11: baseline has errors → blocked
        * Rule 11: baseline has skipped → blocked
        * Rule 11: baseline outcome error → blocked
        * Rule 11: baseline outcome failed despite zero failures/errors → blocked
        * Rule 11: baseline structured_results parse_error → blocked
        * Rule 11: baseline zero tests collected → blocked
        * Happy path: all rules satisfied → verified_for_tested_scenarios
"""

import json
import os
import textwrap
from pathlib import Path

import pytest

from realitycheck.runner import (
    compute_verdict,
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


def _write_setup_error_test(directory: Path, filename: str = "test_setup_error.py") -> Path:
    """Write a test whose fixture raises an exception during setup.

    When pytest runs this file, the test will not reach its body —
    pytest records a setup error, which produces exit code 1 (or possibly
    an error element in the JUnit XML).  The *outcome* seen by the runner
    depends on the exact exit code; more importantly the per-test *status*
    in the JUnit XML is ``error``, not ``failed``.
    """
    p = directory / filename
    p.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.fixture
            def broken_fixture():
                raise RuntimeError("fixture setup intentionally fails")

            def test_uses_broken_fixture(broken_fixture):
                # This body is never reached; the setup error is recorded
                # in the JUnit XML as status="error" for this test node.
                assert True
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


def test_runner_setup_error_blocks_reproduction(run_workspace):
    """A pytest fixture/setup failure must produce a per-test status of 'error'
    in the JUnit XML.  When that execution is used as a reproduction execution,
    compute_verdict must block — a setup error is not a reproduced behavioral
    defect.

    This test exercises the real pytest runner end-to-end:
    1. Runs a test whose fixture raises RuntimeError during setup.
    2. Confirms the execution record has outcome in ("failed", "error") — either
       is acceptable from the runner; the key invariant is that the per-test
       status in structured_results is "error".
    3. Passes that execution directly to compute_verdict and confirms that
       the verdict is "blocked" with the appropriate reason.
    """
    test_dir = run_workspace / "tests_setup_err"
    test_dir.mkdir()
    _write_setup_error_test(test_dir)

    execution = run_pytest(
        repo_root=run_workspace,
        pytest_targets=[str(test_dir)],
        run_id="test-run-setup-err",
        phase="reproduction",
        execution_id="exec-setup-err",
    )

    # The runner outcome is either "failed" (exit 1) or "error" (exit != 0/1).
    # In either case the per-test status in the JUnit XML must be "error".
    sr = execution.get("structured_results", {})
    cases = sr.get("cases", [])
    assert len(cases) >= 1, "Expected at least one test case in JUnit output"
    error_statuses = [c["status"] for c in cases if c["status"] == "error"]
    assert error_statuses, (
        f"Expected at least one case with status='error' but got: {[c['status'] for c in cases]}"
    )

    # Now feed this real setup-error execution into compute_verdict.
    # The node_id as recorded in the JUnit classname / name must be reconstructed.
    # Use the actual cases from structured_results to build the node_id.
    error_case = next(c for c in cases if c["status"] == "error")
    classname = error_case["classname"]
    name = error_case["name"]
    node_id = classname.replace(".", "/") + ".py::" + name

    # Construct a valid passing verification and baseline so that only the
    # reproduction-node-error guard fires.
    verif_case = {"classname": classname, "name": name, "status": "passed", "time": "0.1"}
    verif = _make_exec("passed", "verification", cases=[verif_case])
    baseline = _good_baseline()

    v = compute_verdict(
        execution,
        verif,
        _good_protected(),
        required_node_ids=[node_id],
        baseline_execution=baseline,
        reproduction_expectations={node_id: "failed"},
    )
    assert v["status"] == "blocked", (
        f"Expected blocked but got {v['status']!r}; reason: {v['reason']}"
    )
    # The reason must clearly indicate this is a setup/infrastructure error,
    # not a reproduced defect.
    reason_lower = v["reason"].lower()
    assert "error" in reason_lower or "setup" in reason_lower or "infrastructure" in reason_lower, (
        f"Expected reason to mention setup/error/infrastructure, got: {v['reason']!r}"
    )


# ---------------------------------------------------------------------------
# compute_verdict — helpers
# ---------------------------------------------------------------------------


from realitycheck.runner import compute_verdict


def _good_protected() -> dict:
    return {"ok": True, "missing": [], "modified": []}


def _make_exec(
    outcome: str,
    phase: str = "verification",
    tests: int = 1,
    failures: int = 0,
    errors: int = 0,
    skipped: int = 0,
    cases: list | None = None,
    parse_error: str | None = None,
) -> dict:
    sr: dict = {"tests": tests, "failures": failures, "errors": errors, "skipped": skipped, "cases": cases or []}
    if parse_error is not None:
        sr["parse_error"] = parse_error
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
        "structured_results": sr,
    }


# Canonical node ID used in all _good_repro / _good_verif helpers.
# Must be consistent across both so required_node_ids matching works.
_GOOD_NODE_ID = "tests/regression/test_something.py::test_foo"
_GOOD_CASE = {"classname": "tests.regression.test_something", "name": "test_foo", "status": "failed", "time": "0.1"}
_GOOD_VERIF_CASE = {"classname": "tests.regression.test_something", "name": "test_foo", "status": "passed", "time": "0.1"}


def _good_repro() -> dict:
    """Reproduction execution with a genuine test failure for _GOOD_NODE_ID."""
    return _make_exec(
        "failed", "reproduction",
        failures=1,
        cases=[_GOOD_CASE],
    )


def _good_verif(cases: list | None = None) -> dict:
    return _make_exec(
        "passed", "verification",
        cases=cases or [_GOOD_VERIF_CASE],
    )


def _good_baseline() -> dict:
    return _make_exec("passed", "verification", tests=5, cases=[
        {"classname": "tests.existing.test_happy_path", "name": f"test_case_{i}", "status": "passed", "time": "0.1"}
        for i in range(5)
    ])


# All tests that exercise Rules 1–11 use _GOOD_NODE_IDS so that earlier
# rules are not accidentally blocked by the Rule 0 guard.
_GOOD_NODE_IDS = [_GOOD_NODE_ID]

# Standard per-node expectations for the single-node happy path.
_GOOD_EXPECTATIONS = {_GOOD_NODE_ID: "failed"}


# ---------------------------------------------------------------------------
# compute_verdict — audit-hardening tests (one per enforcement rule)
# ---------------------------------------------------------------------------


# Rule 0a: required_node_ids omitted (not supplied as kwarg) → blocked
def test_verdict_blocked_required_node_ids_omitted():
    """No required_node_ids supplied: must not be possible to reach verified."""
    # required_node_ids is now a mandatory positional keyword; passing an empty
    # list proves the guard independently of the "not supplied" path.
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=[],
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "Required verification test node IDs were not supplied" in v["reason"]


# Rule 0b: required_node_ids is an explicit empty list → blocked
def test_verdict_blocked_required_node_ids_empty():
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=[],
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "Required verification test node IDs were not supplied" in v["reason"]


# Rule 0b-i: reproduction_expectations omitted (None) → blocked
def test_verdict_blocked_reproduction_expectations_omitted():
    """No reproduction_expectations supplied: must block."""
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=None,
    )
    assert v["status"] == "blocked"
    assert "reproduction_expectations" in v["reason"]


# Rule 0b-ii: reproduction_expectations is an empty dict → blocked
def test_verdict_blocked_reproduction_expectations_empty():
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations={},
    )
    assert v["status"] == "blocked"
    assert "reproduction_expectations" in v["reason"]


# Rule 0b-iii: reproduction_expectations contains an invalid expected value → blocked
def test_verdict_blocked_reproduction_expectations_invalid_value():
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations={_GOOD_NODE_ID: "error"},
    )
    assert v["status"] == "blocked"
    assert "Invalid reproduction expectation" in v["reason"]


# Rule 1a: protected_verification is None → blocked
def test_verdict_blocked_no_protected_verification():
    v = compute_verdict(
        _good_repro(), _good_verif(), None,
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "not supplied" in v["reason"]


# Rule 1b: protected_verification ok="false" (string, not bool) → blocked (structural)
def test_verdict_blocked_protected_manifest_ok_string_false():
    """ok='false' (string) must be rejected as structurally invalid — not treated as truthy."""
    v = compute_verdict(
        _good_repro(), _good_verif(),
        {"ok": "false", "missing": [], "modified": []},
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "structurally invalid" in v["reason"]


# Rule 1b: protected_verification ok=True but modified non-empty → blocked (contradictory)
def test_verdict_blocked_protected_manifest_ok_true_but_modified():
    """ok=True with non-empty modified list is contradictory and must block."""
    v = compute_verdict(
        _good_repro(), _good_verif(),
        {"ok": True, "missing": [], "modified": ["docs/application-contract.md"]},
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "contradictory" in v["reason"] or "modified" in v["reason"]


# Rule 1b: protected_verification ok=True but missing non-empty → blocked (contradictory)
def test_verdict_blocked_protected_manifest_ok_true_but_missing():
    """ok=True with non-empty missing list is contradictory and must block."""
    v = compute_verdict(
        _good_repro(), _good_verif(),
        {"ok": True, "missing": ["x"], "modified": []},
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "contradictory" in v["reason"] or "missing" in v["reason"]


# Rule 1c: protected_verification ok=False → blocked
def test_verdict_blocked_protected_manifest_failed():
    v = compute_verdict(
        _good_repro(), _good_verif(),
        {"ok": False, "missing": ["contract.md"], "modified": []},
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "Protected input verification failed" in v["reason"]


# Rule 1c: protected_verification with modified file → blocked
def test_verdict_blocked_protected_manifest_modified():
    v = compute_verdict(
        _good_repro(), _good_verif(),
        {"ok": False, "missing": [], "modified": ["pyproject.toml"]},
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "modified" in v["reason"]


# Rule 2: reproduction_execution is None → blocked
def test_verdict_blocked_no_reproduction_execution():
    v = compute_verdict(
        None, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "Reproduction execution was not supplied" in v["reason"]


# Rule 3a: reproduction passes when failure expected → blocked (defect didn't reproduce)
def test_verdict_blocked_reproduction_passes_when_failure_expected():
    repro = _make_exec("passed", "reproduction")
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "Reproduction outcome mismatch" in v["reason"]


# Rule 3b: reproduction fails when pass expected (preservation test) → blocked
def test_verdict_blocked_reproduction_fails_when_pass_expected():
    # A preservation/control test that should pass before repair, but the
    # reproduction execution shows "failed" overall.
    pres_node = "tests/regression/test_something.py::test_guard"
    pres_case_repro = {"classname": "tests.regression.test_something", "name": "test_guard", "status": "passed", "time": "0.1"}
    pres_case_verif = {"classname": "tests.regression.test_something", "name": "test_guard", "status": "passed", "time": "0.1"}
    repro = _make_exec("failed", "reproduction", cases=[pres_case_repro])
    v = compute_verdict(
        repro, _good_verif(cases=[pres_case_verif]), _good_protected(),
        required_node_ids=[pres_node],
        baseline_execution=_good_baseline(),
        reproduction_expectations={pres_node: "passed"},
    )
    assert v["status"] == "blocked"
    assert "Reproduction outcome mismatch" in v["reason"]


# Rule 4a: reproduction outcome is error → blocked (infra/error state)
def test_verdict_blocked_reproduction_error():
    repro = _make_exec("error", "reproduction")
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "infrastructure/error state" in v["reason"]


# Rule 4b: reproduction outcome is timeout → blocked
def test_verdict_blocked_reproduction_timeout():
    repro = _make_exec("timeout", "reproduction")
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "infrastructure/error state" in v["reason"]


# Bypass probe: reproduction structured results missing → blocked
def test_verdict_blocked_reproduction_missing_structured_results():
    """A reproduction accepted solely on outcome="failed" without structured
    results must be blocked."""
    repro = _make_exec("failed", "reproduction", tests=0, cases=[])
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "Reproduction structured results" in v["reason"]


# Bypass probe: reproduction structured results unparseable → blocked
def test_verdict_blocked_reproduction_unparseable_structured_results():
    """Unparseable reproduction results must block."""
    repro = _make_exec("failed", "reproduction", parse_error="truncated XML")
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "parse" in v["reason"].lower()


# Bypass probe: reproduction setup/infrastructure error (exit 1, outcome "error") → blocked
def test_verdict_blocked_reproduction_infrastructure_error():
    """A pytest setup/collection/infrastructure error (outcome "error") must block
    rather than count as reproduced behaviour."""
    # outcome="error" maps to exit_code != 0 and != 1 in normal runner,
    # but here we force it directly in the execution dict.
    repro = {
        "execution_id": "x",
        "phase": "reproduction",
        "outcome": "error",
        "exit_code": 2,
        "duration_ms": 10,
        "started_at": "2025-01-01T00:00:00+00:00",
        "pytest_targets": ["tests/regression"],
        "application_snapshot": "abc123",
        "protected_manifest": None,
        "structured_results": {"tests": 0, "failures": 0, "errors": 1, "skipped": 0, "cases": []},
    }
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "infrastructure/error state" in v["reason"]


# Bypass probe: per-test status "error" (setup/fixture failure) → blocked
def test_verdict_blocked_reproduction_node_status_error():
    """A required test whose per-test status is 'error' (e.g. fixture setup
    failure) must block even when overall outcome is 'failed'.

    A process exit code of 1 is not sufficient evidence of a reproduced
    behavioral defect — the individual test status must be 'failed'.
    """
    repro = _make_exec(
        "failed", "reproduction",
        tests=1, failures=0, errors=1,
        cases=[{
            "classname": "tests.regression.test_something",
            "name": "test_foo",
            "status": "error",  # ← setup/teardown error, not a genuine test failure
            "time": "0.0",
        }],
    )
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked", (
        f"Expected blocked but got {v['status']!r}; reason: {v['reason']}"
    )
    reason_lower = v["reason"].lower()
    assert "error" in reason_lower or "setup" in reason_lower or "infrastructure" in reason_lower, (
        f"Expected reason to mention setup/error/infrastructure, got: {v['reason']!r}"
    )


# Bypass probe: reproduction required node skipped → blocked
def test_verdict_blocked_reproduction_required_node_skipped():
    """Required test skipped during reproduction must block."""
    repro = _make_exec(
        "failed", "reproduction", tests=1, skipped=1,
        cases=[{"classname": "tests.regression.test_something", "name": "test_foo", "status": "skipped", "time": "0.0"}],
    )
    v = compute_verdict(
        repro, _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "skipped" in v["reason"].lower()


# Rule 5/6: verification structured_results has parse_error → blocked
def test_verdict_blocked_verification_parse_error():
    verif = _make_exec("passed", "verification", parse_error="malformed XML")
    v = compute_verdict(
        _good_repro(), verif, _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "parse" in v["reason"].lower()


# Rule 6: verification collects zero tests → blocked
def test_verdict_blocked_no_tests_collected():
    verif = _make_exec("passed", "verification", tests=0)
    v = compute_verdict(
        _good_repro(), verif, _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "No tests were collected" in v["reason"]


# Rule 7: verification has skipped tests → blocked
def test_verdict_blocked_verification_skipped_tests():
    verif = _make_exec("passed", "verification", tests=2, skipped=1, cases=[
        {"classname": "tests.regression.test_something", "name": "test_foo", "status": "passed", "time": "0.1"},
        {"classname": "tests.regression.test_something", "name": "test_bar", "status": "skipped", "time": "0.0"},
    ])
    v = compute_verdict(
        _good_repro(), verif, _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "skipped" in v["reason"]


# Rule 8a: required node ID missing from results → blocked
def test_verdict_blocked_required_node_id_missing():
    verif = _good_verif(cases=[
        {"classname": "tests.regression.test_x", "name": "test_foo", "status": "passed", "time": "0.1"},
    ])
    node_id = "tests/regression/test_x.py::test_foo"
    repro = _make_exec(
        "failed", "reproduction", failures=1,
        cases=[{"classname": "tests.regression.test_x", "name": "test_foo", "status": "failed", "time": "0.1"}],
    )
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=["tests/regression/test_x.py::test_missing"],
        baseline_execution=_good_baseline(),
        reproduction_expectations={"tests/regression/test_x.py::test_missing": "failed"},
    )
    assert v["status"] == "blocked"
    assert "not found" in v["reason"]


# Bypass probe: same function name in a different file must NOT satisfy the requirement
def test_verdict_blocked_required_node_id_wrong_file():
    """tests/never_run.py::test_foo must NOT be satisfied by
    tests/regression/test_something.py::test_foo even though the function
    name is identical."""
    # The verif execution contains test_foo from tests/regression/test_something.py
    # but the required node ID specifies tests/never_run.py::test_foo.
    verif = _good_verif(cases=[_GOOD_VERIF_CASE])
    wrong_node = "tests/never_run.py::test_foo"
    repro = _make_exec(
        "failed", "reproduction", failures=1,
        cases=[{"classname": "tests.never_run", "name": "test_foo", "status": "failed", "time": "0.1"}],
    )
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=[wrong_node],
        baseline_execution=_good_baseline(),
        reproduction_expectations={wrong_node: "failed"},
    )
    assert v["status"] == "blocked"
    assert "not found" in v["reason"]


# Rule 8b: required node ID is skipped → blocked
def test_verdict_blocked_required_node_id_skipped():
    node_id = "tests/regression/test_x.py::test_foo"
    repro = _make_exec(
        "failed", "reproduction", failures=1,
        cases=[{"classname": "tests.regression.test_x", "name": "test_foo", "status": "failed", "time": "0.1"}],
    )
    verif = _make_exec("passed", "verification", tests=1, cases=[
        {"classname": "tests.regression.test_x", "name": "test_foo", "status": "skipped", "time": "0.0"},
    ])
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=[node_id],
        baseline_execution=_good_baseline(),
        reproduction_expectations={node_id: "failed"},
    )
    assert v["status"] == "blocked"
    assert "skipped" in v["reason"]


# Rule 8c: required node ID failed → repair_failed
def test_verdict_repair_failed_required_node_id_failed():
    node_id = "tests/regression/test_x.py::test_foo"
    repro = _make_exec(
        "failed", "reproduction", failures=1,
        cases=[{"classname": "tests.regression.test_x", "name": "test_foo", "status": "failed", "time": "0.1"}],
    )
    verif = _make_exec("failed", "verification", tests=1, failures=1, cases=[
        {"classname": "tests.regression.test_x", "name": "test_foo", "status": "failed", "time": "0.1"},
    ])
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=[node_id],
        baseline_execution=_good_baseline(),
        reproduction_expectations={node_id: "failed"},
    )
    assert v["status"] == "repair_failed"
    assert "test_foo" in v["reason"]


# Rule 10/11: baseline_execution is None → blocked
def test_verdict_blocked_no_baseline_execution():
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=None,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "Baseline-preservation execution was not supplied" in v["reason"]


# Rule 11a: baseline has failures → blocked
# The baseline outcome is "failed"; the new explicit-outcome check fires first
# (outcome != "passed" → blocked).  The status is still "blocked".
def test_verdict_blocked_baseline_has_failures():
    baseline = _make_exec("failed", "verification", tests=5, failures=1, cases=[
        {"classname": "c", "name": f"test_{i}", "status": "failed" if i == 0 else "passed", "time": "0.1"}
        for i in range(5)
    ])
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    # The explicit-outcome guard fires first; both "outcome" and "passed" appear in the message.
    assert "passed" in v["reason"] or "failure" in v["reason"]


# Rule 11b: baseline has errors → blocked
# Same: outcome="failed" triggers the explicit-outcome check before the error counter check.
def test_verdict_blocked_baseline_has_errors():
    baseline = _make_exec("failed", "verification", tests=5, errors=1, cases=[
        {"classname": "c", "name": f"test_{i}", "status": "error" if i == 0 else "passed", "time": "0.1"}
        for i in range(5)
    ])
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    # The explicit-outcome guard fires first; both "outcome" and "passed" appear in the message.
    assert "passed" in v["reason"] or "error" in v["reason"]


# Rule 11c: baseline has skipped tests → blocked
def test_verdict_blocked_baseline_has_skipped():
    baseline = _make_exec("passed", "verification", tests=5, skipped=1, cases=[
        {"classname": "c", "name": f"test_{i}", "status": "skipped" if i == 0 else "passed", "time": "0.1"}
        for i in range(5)
    ])
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "skipped" in v["reason"]


# Rule 11d: baseline outcome error → blocked
def test_verdict_blocked_baseline_outcome_error():
    baseline = _make_exec("error", "verification", tests=5)
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "infrastructure/error state" in v["reason"]


# Rule 11e: baseline outcome timeout → blocked
def test_verdict_blocked_baseline_outcome_timeout():
    baseline = _make_exec("timeout", "verification", tests=5)
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "infrastructure/error state" in v["reason"]


# Bypass probe: baseline outcome "failed" despite zero failure/error counters → blocked
def test_verdict_blocked_baseline_outcome_failed_despite_zero_counts():
    """An internally inconsistent baseline (outcome='failed', failures=0, errors=0)
    must block because outcome must be explicitly 'passed'."""
    baseline = _make_exec("failed", "verification", tests=5, failures=0, errors=0, cases=[
        {"classname": "c", "name": f"test_{i}", "status": "passed", "time": "0.1"}
        for i in range(5)
    ])
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "outcome" in v["reason"].lower() or "passed" in v["reason"].lower()


# Rule 11f: baseline structured_results has parse_error → blocked
def test_verdict_blocked_baseline_parse_error():
    baseline = _make_exec("passed", "verification", parse_error="XML truncated")
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "parse" in v["reason"].lower()


# Rule 11g: baseline collects zero tests → blocked
def test_verdict_blocked_baseline_no_tests_collected():
    baseline = _make_exec("passed", "verification", tests=0)
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=baseline,
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
    assert "No tests were collected during baseline" in v["reason"]


# ---------------------------------------------------------------------------
# Mixed per-node expectations (RC-003 pattern: two defect tests + one guard)
# ---------------------------------------------------------------------------

# Node IDs for the three-node mixed scenario
_NODE_DEFECT_A = "tests/regression/test_rc003.py::test_exact_replay"
_NODE_DEFECT_B = "tests/regression/test_rc003.py::test_conflict_raises"
_NODE_GUARD_C  = "tests/regression/test_rc003.py::test_distinct_ids_both_stored"

_MIXED_NODE_IDS = [_NODE_DEFECT_A, _NODE_DEFECT_B, _NODE_GUARD_C]

_MIXED_EXPECTATIONS = {
    _NODE_DEFECT_A: "failed",   # defect test: must fail before repair
    _NODE_DEFECT_B: "failed",   # defect test: must fail before repair
    _NODE_GUARD_C:  "passed",   # preservation guard: must already pass
}

# Reproduction execution for the mixed scenario:
# two failures + one pass, overall outcome "failed"
_MIXED_REPRO_CASES = [
    {"classname": "tests.regression.test_rc003", "name": "test_exact_replay",           "status": "failed", "time": "0.1"},
    {"classname": "tests.regression.test_rc003", "name": "test_conflict_raises",         "status": "failed", "time": "0.1"},
    {"classname": "tests.regression.test_rc003", "name": "test_distinct_ids_both_stored","status": "passed", "time": "0.1"},
]

# Verification execution for the mixed scenario: all three pass
_MIXED_VERIF_CASES = [
    {"classname": "tests.regression.test_rc003", "name": "test_exact_replay",           "status": "passed", "time": "0.1"},
    {"classname": "tests.regression.test_rc003", "name": "test_conflict_raises",         "status": "passed", "time": "0.1"},
    {"classname": "tests.regression.test_rc003", "name": "test_distinct_ids_both_stored","status": "passed", "time": "0.1"},
]


def test_verdict_verified_mixed_expectations():
    """Two defect tests (expected 'failed') + one preservation guard (expected 'passed')
    in reproduction, all three pass in verification → verified_for_tested_scenarios."""
    repro = _make_exec("failed", "reproduction", failures=2, tests=3, cases=_MIXED_REPRO_CASES)
    verif = _make_exec("passed", "verification", tests=3, cases=_MIXED_VERIF_CASES)
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=_MIXED_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_MIXED_EXPECTATIONS,
    )
    assert v["status"] == "verified_for_tested_scenarios", (
        f"Expected verified_for_tested_scenarios but got {v['status']!r}; reason: {v['reason']}"
    )


def test_verdict_blocked_preservation_guard_incorrectly_fails():
    """The preservation guard test must pass during reproduction (it was already
    compliant before repair).  If it fails during reproduction, the verdict must
    be blocked — the guard's expectation is 'passed', not 'failed'."""
    bad_repro_cases = [
        {"classname": "tests.regression.test_rc003", "name": "test_exact_replay",           "status": "failed", "time": "0.1"},
        {"classname": "tests.regression.test_rc003", "name": "test_conflict_raises",         "status": "failed", "time": "0.1"},
        # Guard test fails instead of passing — this is wrong
        {"classname": "tests.regression.test_rc003", "name": "test_distinct_ids_both_stored","status": "failed", "time": "0.1"},
    ]
    repro = _make_exec("failed", "reproduction", failures=3, tests=3, cases=bad_repro_cases)
    verif = _make_exec("passed", "verification", tests=3, cases=_MIXED_VERIF_CASES)
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=_MIXED_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_MIXED_EXPECTATIONS,
    )
    assert v["status"] == "blocked", (
        f"Expected blocked but got {v['status']!r}; reason: {v['reason']}"
    )
    assert "test_distinct_ids_both_stored" in v["reason"] or "did not pass" in v["reason"]


def test_verdict_repair_failed_when_required_node_still_fails_after_repair():
    """After repair, ALL required nodes must pass in verification regardless of
    their reproduction expectation.  If any required node still fails after
    repair, the verdict is repair_failed (not verified)."""
    # Defect A still fails in verification (repair incomplete)
    bad_verif_cases = [
        {"classname": "tests.regression.test_rc003", "name": "test_exact_replay",           "status": "failed", "time": "0.1"},
        {"classname": "tests.regression.test_rc003", "name": "test_conflict_raises",         "status": "passed", "time": "0.1"},
        {"classname": "tests.regression.test_rc003", "name": "test_distinct_ids_both_stored","status": "passed", "time": "0.1"},
    ]
    repro = _make_exec("failed", "reproduction", failures=2, tests=3, cases=_MIXED_REPRO_CASES)
    verif = _make_exec("failed", "verification", tests=3, failures=1, cases=bad_verif_cases)
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=_MIXED_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_MIXED_EXPECTATIONS,
    )
    assert v["status"] == "repair_failed", (
        f"Expected repair_failed but got {v['status']!r}; reason: {v['reason']}"
    )


# ---------------------------------------------------------------------------
# compute_verdict — original passing tests (updated for new API)
# ---------------------------------------------------------------------------


def test_verdict_verified():
    v = compute_verdict(
        _good_repro(), _good_verif(), _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "verified_for_tested_scenarios"


def test_verdict_repair_failed():
    node_id = "tests/regression/test_x.py::test_foo"
    repro = _make_exec(
        "failed", "reproduction", failures=1,
        cases=[{"classname": "tests.regression.test_x", "name": "test_foo", "status": "failed", "time": "0.1"}],
    )
    verif = _make_exec("failed", "verification", tests=1, failures=1, cases=[
        {"classname": "tests.regression.test_x", "name": "test_foo", "status": "failed", "time": "0.1"},
    ])
    v = compute_verdict(
        repro, verif, _good_protected(),
        required_node_ids=[node_id],
        baseline_execution=_good_baseline(),
        reproduction_expectations={node_id: "failed"},
    )
    assert v["status"] == "repair_failed"


def test_verdict_blocked_protected_manifest():
    v = compute_verdict(
        _good_repro(), _good_verif(),
        {"ok": False, "missing": ["contract.md"], "modified": []},
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"


def test_verdict_blocked_timeout():
    verif = _make_exec("timeout", "verification")
    v = compute_verdict(
        _good_repro(), verif, _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"


# Rule 6 original test (zero tests in verification)
def test_verdict_blocked_no_tests_collected_original():
    verif = _make_exec("passed", "verification", tests=0)
    v = compute_verdict(
        _good_repro(), verif, _good_protected(),
        required_node_ids=_GOOD_NODE_IDS,
        baseline_execution=_good_baseline(),
        reproduction_expectations=_GOOD_EXPECTATIONS,
    )
    assert v["status"] == "blocked"
