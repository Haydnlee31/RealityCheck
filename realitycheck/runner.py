"""
RealityCheck deterministic runner.

Responsibilities
----------------
* sha256_file            — hash a single file
* create_protected_manifest — record expected hashes for a set of files
* verify_protected_manifest — compare actual hashes against recorded ones
* snapshot_application   — hash all .py files under a source directory
* run_pytest             — invoke pytest deterministically (no shell=True)
* record_execution       — assemble and persist an execution.json artifact
* compute_verdict        — emit a deterministic verdict from an execution record
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_OUTCOMES = frozenset({"passed", "failed", "error", "timeout"})
ALLOWED_PHASES = frozenset({"baseline", "reproduction", "verification", "independent"})

# ---------------------------------------------------------------------------
# Hashing utilities
# ---------------------------------------------------------------------------


def sha256_file(path: str | Path) -> str:
    """Return the lowercase hex SHA-256 digest of the file at *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Protected manifest
# ---------------------------------------------------------------------------


def create_protected_manifest(
    repo_root: str | Path,
    paths: list[str | Path],
    output_path: str | Path,
) -> dict[str, Any]:
    """Hash each path in *paths* (relative to *repo_root*) and write a
    manifest JSON file to *output_path*.

    Returns the manifest dict.
    """
    repo_root = Path(repo_root).resolve()
    entries: list[dict[str, str]] = []
    for p in sorted(str(x) for x in paths):
        abs_path = repo_root / p
        entries.append(
            {
                "relative_path": str(p),
                "sha256": sha256_file(abs_path),
            }
        )
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": entries,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2))
    return manifest


def verify_protected_manifest(
    repo_root: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Verify that every file in *manifest_path* still matches its recorded
    hash.

    Returns a result dict::

        {
            "ok": bool,
            "missing": [relative_path, ...],
            "modified": [relative_path, ...],
        }

    Does NOT silently regenerate hashes.
    """
    repo_root = Path(repo_root).resolve()
    manifest = json.loads(Path(manifest_path).read_text())
    missing: list[str] = []
    modified: list[str] = []
    for entry in manifest["files"]:
        rel = entry["relative_path"]
        abs_path = repo_root / rel
        if not abs_path.exists():
            missing.append(rel)
        else:
            actual = sha256_file(abs_path)
            if actual != entry["sha256"]:
                modified.append(rel)
    return {
        "ok": not missing and not modified,
        "missing": missing,
        "modified": modified,
    }


# ---------------------------------------------------------------------------
# Application snapshot
# ---------------------------------------------------------------------------


def snapshot_application(source_dir: str | Path) -> dict[str, Any]:
    """Hash every .py file under *source_dir* and return a snapshot dict::

        {
            "source_dir": str,
            "files": [{"relative_path": str, "sha256": str}, ...],
            "snapshot_id": str,   # deterministic combined digest
        }
    """
    source_dir = Path(source_dir).resolve()
    entries: list[dict[str, str]] = []
    for py_file in sorted(source_dir.rglob("*.py")):
        rel = str(py_file.relative_to(source_dir))
        entries.append({"relative_path": rel, "sha256": sha256_file(py_file)})

    # Combined snapshot id: sha256 of "<rel>:<hash>\n" lines (sorted)
    combined = hashlib.sha256()
    for e in entries:
        combined.update(f"{e['relative_path']}:{e['sha256']}\n".encode())

    return {
        "source_dir": str(source_dir),
        "files": entries,
        "snapshot_id": combined.hexdigest(),
    }


# ---------------------------------------------------------------------------
# Environment manifest
# ---------------------------------------------------------------------------


def _environment_manifest(repo_root: Path) -> dict[str, Any]:
    """Return a minimal environment manifest."""
    try:
        import pytest as _pytest

        pytest_version = _pytest.__version__
    except ImportError:
        pytest_version = "unknown"

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "pytest_version": pytest_version,
        "working_directory": str(repo_root),
    }


# ---------------------------------------------------------------------------
# JUnit XML parsing
# ---------------------------------------------------------------------------


def _parse_junit(xml_path: Path) -> dict[str, Any]:
    """Parse a JUnit XML file produced by pytest and return summary counts."""
    try:
        tree = ET.parse(xml_path)
    except Exception as exc:
        return {"parse_error": str(exc)}

    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return {"parse_error": "no <testsuite> element found"}

    attrs = suite.attrib
    cases: list[dict[str, Any]] = []
    for tc in suite.iter("testcase"):
        status = "passed"
        if tc.find("failure") is not None:
            status = "failed"
        elif tc.find("error") is not None:
            status = "error"
        elif tc.find("skipped") is not None:
            status = "skipped"
        cases.append(
            {
                "classname": tc.get("classname", ""),
                "name": tc.get("name", ""),
                "status": status,
                "time": tc.get("time"),
            }
        )
    return {
        "tests": int(attrs.get("tests", 0)),
        "failures": int(attrs.get("failures", 0)),
        "errors": int(attrs.get("errors", 0)),
        "skipped": int(attrs.get("skipped", 0)),
        "time": attrs.get("time"),
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Deterministic pytest runner
# ---------------------------------------------------------------------------


def run_pytest(
    repo_root: str | Path,
    pytest_targets: list[str],
    run_id: str,
    phase: str,
    execution_id: str | None = None,
    timeout: int = 120,
    extra_args: list[str] | None = None,
    protected_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    """Invoke pytest deterministically and record a structured execution record.

    Parameters
    ----------
    repo_root:
        Repository root (used as cwd and anchor for relative paths).
    pytest_targets:
        List of pytest target strings, e.g. ``["tests/existing"]``.
        Arbitrary shell commands are not accepted.
    run_id:
        Identifier for the parent run (groups multiple executions).
    phase:
        One of ``baseline``, ``reproduction``, ``verification``, ``independent``.
    execution_id:
        If omitted a UUID is generated.
    timeout:
        Wall-clock timeout in seconds.
    extra_args:
        Additional pytest flags (e.g. ``["-x"]``).  No shell metacharacters.
    protected_manifest_path:
        If provided, ``verify_protected_manifest`` is called and the result
        is embedded in the execution record.

    Returns
    -------
    The execution record dict (same content as execution.json).
    """
    if phase not in ALLOWED_PHASES:
        raise ValueError(f"phase must be one of {sorted(ALLOWED_PHASES)}, got {phase!r}")

    repo_root = Path(repo_root).resolve()
    execution_id = execution_id or str(uuid.uuid4())
    exec_dir = repo_root / "runs" / run_id / execution_id
    exec_dir.mkdir(parents=True, exist_ok=True)

    junit_path = exec_dir / "junit.xml"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"--junitxml={junit_path}",
        "-p",
        "no:cacheprovider",
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend(pytest_targets)

    # --- capture environment before run ---
    env_manifest = _environment_manifest(repo_root)
    app_snapshot = snapshot_application(repo_root / "sample_app")
    protected_result: dict[str, Any] | None = None
    if protected_manifest_path is not None:
        protected_result = verify_protected_manifest(repo_root, protected_manifest_path)

    started_at = datetime.now(timezone.utc)
    t0 = time.monotonic()
    timed_out = False
    proc_stdout = ""
    proc_stderr = ""
    exit_code = -1

    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        proc_stdout = result.stdout
        proc_stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        proc_stdout = exc.stdout or ""
        proc_stderr = exc.stderr or ""
        if isinstance(proc_stdout, bytes):
            proc_stdout = proc_stdout.decode(errors="replace")
        if isinstance(proc_stderr, bytes):
            proc_stderr = proc_stderr.decode(errors="replace")
        exit_code = -1

    duration_ms = int((time.monotonic() - t0) * 1000)

    # --- derive outcome ---
    if timed_out:
        outcome = "timeout"
    elif exit_code == 0:
        outcome = "passed"
    elif exit_code == 1:
        outcome = "failed"
    else:
        outcome = "error"

    # --- write text artifacts ---
    (exec_dir / "stdout.txt").write_text(proc_stdout)
    (exec_dir / "stderr.txt").write_text(proc_stderr)

    # --- parse JUnit XML ---
    structured_results: dict[str, Any] = {}
    if junit_path.exists():
        structured_results = _parse_junit(junit_path)

    # --- write application-snapshot.json ---
    snap_path = exec_dir / "application-snapshot.json"
    snap_path.write_text(json.dumps(app_snapshot, indent=2))

    # --- write environment.json ---
    env_path = exec_dir / "environment.json"
    env_path.write_text(json.dumps(env_manifest, indent=2))

    # --- assemble execution record ---
    execution = {
        "execution_id": execution_id,
        "phase": phase,
        "started_at": started_at.isoformat(),
        "duration_ms": duration_ms,
        "exit_code": exit_code,
        "outcome": outcome,
        "pytest_targets": pytest_targets,
        "application_snapshot": app_snapshot["snapshot_id"],
        "protected_manifest": protected_result,
        "environment_manifest": str(env_path.relative_to(repo_root)),
        "stdout": str((exec_dir / "stdout.txt").relative_to(repo_root)),
        "stderr": str((exec_dir / "stderr.txt").relative_to(repo_root)),
        "structured_results": structured_results,
    }

    (exec_dir / "execution.json").write_text(json.dumps(execution, indent=2))
    return execution


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------


def compute_verdict(
    reproduction_execution: dict[str, Any],
    verification_execution: dict[str, Any],
    protected_verification: dict[str, Any] | None,
    *,
    required_node_ids: list[str],
    baseline_execution: dict[str, Any] | None = None,
    reproduction_expectations: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute a deterministic verdict.

    Parameters
    ----------
    reproduction_execution:
        The execution record from the reproduction phase.  Must not be None.
    verification_execution:
        The execution record from the post-repair verification phase.
    protected_verification:
        The result of ``verify_protected_manifest``.  A value of ``None``
        is treated as a hard block — absent protected-manifest verification
        can never allow a ``verified_for_tested_scenarios`` verdict.
        Must be a dict with boolean ``ok``, list ``missing``, and list
        ``modified``.  A structurally invalid result (e.g. ``ok`` is a
        string, or missing/modified are absent) is treated as a hard block.
    required_node_ids:
        Mandatory, non-empty list of canonical pytest node IDs
        (``path/to/test_file.py::test_function``) that must appear and pass
        in both the reproduction and verification structured results.
        An empty list or a missing value is a hard block — a
        ``verified_for_tested_scenarios`` verdict cannot be issued without
        knowing which specific tests were required.
        Matching is exact: ``tests/a.py::test_foo`` is NOT satisfied by
        ``tests/b.py::test_foo`` even if the function name is the same.
    baseline_execution:
        Execution record for the post-repair baseline (existing-tests) run.
        When supplied, it must show outcome == "passed" with zero failures,
        errors, and no skips.  Absence of this argument is itself a hard
        block.
    reproduction_expectations:
        Mandatory per-node mapping of ``{node_id: expected_status}`` where
        ``expected_status`` is either ``"failed"`` (defect test — must fail
        before repair) or ``"passed"`` (preservation/control test — must
        already pass before repair).  The mapping must be supplied and
        non-empty; its keys define the complete required reproduction node
        set (which must match ``required_node_ids`` exactly).
        ``"failed"`` means the actual test status must be ``"failed"``
        (never ``"error"``).  A setup error, teardown error, collection error,
        or infrastructure error whose per-test status is ``"error"`` always
        blocks verification, even when the overall outcome is ``"failed"``.
        ``"passed"`` means the actual test status must be ``"passed"``.
        ``"skipped"``/``"error"``/missing nodes always block.
        After repair, every required node must pass during verification
        regardless of its reproduction expectation.

    Returns
    -------
    ``{"status": str, "reason": str, "limitations": list[str]}``

    Enforcement rules
    -----------------
    A ``verified_for_tested_scenarios`` verdict requires ALL of the following:

    1. protected_verification is not None, is structurally valid
       (dict with bool ok, list missing, list modified), and ok is True
       with both missing and modified empty.
    2. reproduction_execution is not None (never defaults to success).
    3. reproduction outcome matches the global expectation derived from the
       per-node mapping:
       - all nodes expect "failed" → overall outcome must be "failed";
       - all nodes expect "passed" → overall outcome must be "passed";
       - mixed → overall outcome must be "failed" (some defect tests present).
    4. reproduction outcome must not be "error" or "timeout".
    5. verification structured_results must be present and free of parse errors.
    6. At least one test must have been collected (tests > 0).
    7. No test may be skipped during verification.
    8. required_node_ids must be non-empty; every listed canonical node ID must
       be present in the JUnit output by exact path match and must not be
       skipped or failed.  A same-named function in a different file does NOT
       satisfy the requirement.
    9. reproduction_expectations must be supplied and non-empty; every required
       node must appear in structured reproduction results with its exact
       expected status:
       - "failed" expectation → per-test status must be "failed" (never "error");
       - "passed" expectation → per-test status must be "passed".
    10. baseline_execution must be supplied (None → blocked).
    11. baseline_execution outcome must be "passed" and structured results must
        show zero failures, errors, and skipped tests.
    """
    limitations: list[str] = []

    # ------------------------------------------------------------------ #
    # Rule 0: required_node_ids must be provided and non-empty            #
    # ------------------------------------------------------------------ #
    if not required_node_ids:
        return {
            "status": "blocked",
            "reason": "Required verification test node IDs were not supplied",
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 0b: reproduction_expectations must be supplied and non-empty   #
    # ------------------------------------------------------------------ #
    if not reproduction_expectations:
        return {
            "status": "blocked",
            "reason": (
                "Per-node reproduction_expectations mapping was not supplied or is empty; "
                "every required node must have an explicit expected status "
                "('failed' or 'passed')"
            ),
            "limitations": limitations,
        }
    for nid, exp in reproduction_expectations.items():
        if exp not in ("failed", "passed"):
            return {
                "status": "blocked",
                "reason": (
                    f"Invalid reproduction expectation {exp!r} for node '{nid}'; "
                    f"allowed values are 'failed' and 'passed'"
                ),
                "limitations": limitations,
            }

    # ------------------------------------------------------------------ #
    # Rule 1: protected_verification must be present, structurally valid, #
    # and ok == True with empty missing and modified lists                #
    # ------------------------------------------------------------------ #
    if protected_verification is None:
        return {
            "status": "blocked",
            "reason": "Protected-manifest verification was not supplied",
            "limitations": limitations,
        }
    # Structural validation — must be a dict with boolean ok, list missing, list modified
    _pv_ok = protected_verification.get("ok") if isinstance(protected_verification, dict) else None
    _pv_missing = protected_verification.get("missing") if isinstance(protected_verification, dict) else None
    _pv_modified = protected_verification.get("modified") if isinstance(protected_verification, dict) else None
    if (
        not isinstance(protected_verification, dict)
        or not isinstance(_pv_ok, bool)
        or not isinstance(_pv_missing, list)
        or not isinstance(_pv_modified, list)
    ):
        return {
            "status": "blocked",
            "reason": (
                "Protected-manifest verification result is structurally invalid — "
                "must be a dict with boolean 'ok', list 'missing', and list 'modified'"
            ),
            "limitations": limitations,
        }
    if not _pv_ok:
        parts = []
        if _pv_missing:
            parts.append(f"missing: {_pv_missing}")
        if _pv_modified:
            parts.append(f"modified: {_pv_modified}")
        detail = "; ".join(parts) if parts else "ok is False"
        return {
            "status": "blocked",
            "reason": f"Protected input verification failed — {detail}",
            "limitations": limitations,
        }
    # ok is True — both lists must be empty
    if _pv_missing or _pv_modified:
        parts = []
        if _pv_missing:
            parts.append(f"missing: {_pv_missing}")
        if _pv_modified:
            parts.append(f"modified: {_pv_modified}")
        return {
            "status": "blocked",
            "reason": (
                f"Protected input verification result is contradictory: "
                f"ok is True but {'; '.join(parts)}"
            ),
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 2: reproduction_execution must be present                      #
    # ------------------------------------------------------------------ #
    if reproduction_execution is None:
        return {
            "status": "blocked",
            "reason": "Reproduction execution was not supplied",
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 4: reproduction must not be error or timeout                   #
    # ------------------------------------------------------------------ #
    if reproduction_execution["outcome"] in ("error", "timeout"):
        return {
            "status": "blocked",
            "reason": (
                f"Reproduction execution ended in an infrastructure/error state "
                f"(outcome: {reproduction_execution['outcome']})"
            ),
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 3: reproduction outcome must match expectation derived from    #
    # per-node mapping: any "failed" node → overall must be "failed";     #
    # all "passed" nodes → overall must be "passed".                      #
    # ------------------------------------------------------------------ #
    _has_failed_expectation = any(v == "failed" for v in reproduction_expectations.values())
    _expected_overall = "failed" if _has_failed_expectation else "passed"
    if reproduction_execution["outcome"] != _expected_overall:
        return {
            "status": "blocked",
            "reason": (
                f"Reproduction outcome mismatch: expected "
                f"'{_expected_overall}', got "
                f"'{reproduction_execution['outcome']}'"
            ),
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 9 (reproduction): validate reproduction structured results     #
    # and confirm required node IDs have the expected per-test outcome    #
    # ------------------------------------------------------------------ #
    rsr = reproduction_execution.get("structured_results") or {}
    if rsr.get("parse_error"):
        return {
            "status": "blocked",
            "reason": (
                f"Reproduction structured results could not be parsed: {rsr['parse_error']}"
            ),
            "limitations": limitations,
        }
    if not rsr or rsr.get("tests", 0) == 0:
        return {
            "status": "blocked",
            "reason": "Reproduction structured results are missing or contain no test cases",
            "limitations": limitations,
        }

    # Build exact-match lookup keyed by canonical pytest node ID
    # JUnit classname uses dots for path separators; name is the function.
    repro_case_lookup = _build_exact_node_lookup(rsr.get("cases", []))

    for node_id in required_node_ids:
        expected_repro_status = reproduction_expectations.get(node_id)
        if expected_repro_status is None:
            # Node is required but has no expectation entry — block
            return {
                "status": "blocked",
                "reason": (
                    f"Required node '{node_id}' has no entry in reproduction_expectations"
                ),
                "limitations": limitations,
            }
        if node_id not in repro_case_lookup:
            return {
                "status": "blocked",
                "reason": (
                    f"Required test node '{node_id}' was not found in "
                    f"reproduction structured results"
                ),
                "limitations": limitations,
            }
        repro_status = repro_case_lookup[node_id]
        if repro_status == "skipped":
            return {
                "status": "blocked",
                "reason": (
                    f"Required test node '{node_id}' was skipped during reproduction"
                ),
                "limitations": limitations,
            }
        if repro_status == "error":
            # A setup/teardown/collection error is never a reproduced defect —
            # it is an infrastructure failure regardless of expectation.
            return {
                "status": "blocked",
                "reason": (
                    f"Required test node '{node_id}' ended with status 'error' during "
                    f"reproduction; a setup/teardown/collection error is not a reproduced "
                    f"behavioral defect — a genuine test failure is required"
                ),
                "limitations": limitations,
            }
        # Per-node expectation check:
        # "failed" → status must be "failed" (error already blocked above)
        # "passed" → status must be "passed"
        if expected_repro_status == "failed" and repro_status != "failed":
            return {
                "status": "blocked",
                "reason": (
                    f"Required test node '{node_id}' did not fail during reproduction "
                    f"(status: {repro_status!r}); a genuine test failure is required"
                ),
                "limitations": limitations,
            }
        if expected_repro_status == "passed" and repro_status != "passed":
            return {
                "status": "blocked",
                "reason": (
                    f"Required test node '{node_id}' did not pass during reproduction "
                    f"(status: {repro_status!r}); a passing result is required"
                ),
                "limitations": limitations,
            }

    # ------------------------------------------------------------------ #
    # Rule 9 / Rule 8: verification execution checks                      #
    # ------------------------------------------------------------------ #
    if verification_execution["outcome"] == "timeout":
        return {
            "status": "blocked",
            "reason": "Verification execution timed out",
            "limitations": limitations,
        }

    if verification_execution["outcome"] == "error":
        return {
            "status": "blocked",
            "reason": (
                f"Verification execution exited with error "
                f"(exit code {verification_execution['exit_code']})"
            ),
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 6: structured results must be parseable                        #
    # ------------------------------------------------------------------ #
    sr = verification_execution.get("structured_results") or {}
    if sr.get("parse_error"):
        return {
            "status": "blocked",
            "reason": f"Verification structured results could not be parsed: {sr['parse_error']}",
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 6: at least one test must have been collected                  #
    # ------------------------------------------------------------------ #
    if sr.get("tests", 0) == 0:
        return {
            "status": "blocked",
            "reason": "No tests were collected during verification",
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 8: required node IDs must be present and passing (exact match) #
    # ------------------------------------------------------------------ #
    verif_case_lookup = _build_exact_node_lookup(sr.get("cases", []))

    for node_id in required_node_ids:
        if node_id not in verif_case_lookup:
            return {
                "status": "blocked",
                "reason": (
                    f"Required test node '{node_id}' was not found in "
                    f"verification structured results"
                ),
                "limitations": limitations,
            }
        status = verif_case_lookup[node_id]
        if status == "skipped":
            return {
                "status": "blocked",
                "reason": f"Required test node '{node_id}' was skipped during verification",
                "limitations": limitations,
            }
        if status in ("failed", "error"):
            return {
                "status": "repair_failed",
                "reason": f"Required test node '{node_id}' {status} during verification",
                "limitations": limitations,
            }

    # ------------------------------------------------------------------ #
    # Rule 7: any skipped test blocks the verdict                         #
    # ------------------------------------------------------------------ #
    if sr.get("skipped", 0) > 0:
        return {
            "status": "blocked",
            "reason": (
                f"{sr['skipped']} required verification test(s) were skipped"
            ),
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 10 / Rule 11: baseline_execution must be supplied and pass     #
    # ------------------------------------------------------------------ #
    if baseline_execution is None:
        return {
            "status": "blocked",
            "reason": "Baseline-preservation execution was not supplied",
            "limitations": limitations,
        }

    bsr = baseline_execution.get("structured_results") or {}
    if bsr.get("parse_error"):
        return {
            "status": "blocked",
            "reason": (
                f"Baseline structured results could not be parsed: {bsr['parse_error']}"
            ),
            "limitations": limitations,
        }

    if baseline_execution["outcome"] in ("error", "timeout"):
        return {
            "status": "blocked",
            "reason": (
                f"Baseline execution ended in an infrastructure/error state "
                f"(outcome: {baseline_execution['outcome']})"
            ),
            "limitations": limitations,
        }

    # Rule 11: baseline outcome must explicitly be "passed"
    if baseline_execution["outcome"] != "passed":
        return {
            "status": "blocked",
            "reason": (
                f"Baseline execution outcome is '{baseline_execution['outcome']}'; "
                f"outcome must be 'passed' for a valid baseline"
            ),
            "limitations": limitations,
        }

    if bsr.get("tests", 0) == 0:
        return {
            "status": "blocked",
            "reason": "No tests were collected during baseline execution",
            "limitations": limitations,
        }

    if bsr.get("failures", 0) > 0 or bsr.get("errors", 0) > 0:
        return {
            "status": "blocked",
            "reason": (
                f"Baseline execution has "
                f"{bsr.get('failures', 0)} failure(s) and "
                f"{bsr.get('errors', 0)} error(s)"
            ),
            "limitations": limitations,
        }

    if bsr.get("skipped", 0) > 0:
        return {
            "status": "blocked",
            "reason": (
                f"Baseline execution has {bsr['skipped']} skipped test(s)"
            ),
            "limitations": limitations,
        }

    # ------------------------------------------------------------------ #
    # Rule 9: final verification outcome check                            #
    # ------------------------------------------------------------------ #
    if verification_execution["outcome"] == "passed":
        limitations.append(
            "Verdict covers only the tested scenarios — not all contract requirements."
        )
        return {
            "status": "verified_for_tested_scenarios",
            "reason": "Verification execution passed all required tests",
            "limitations": limitations,
        }

    return {
        "status": "repair_failed",
        "reason": "Verification execution did not pass",
        "limitations": limitations,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_exact_node_lookup(cases: list[dict[str, Any]]) -> dict[str, str]:
    """Build a mapping from canonical pytest node ID to test status.

    JUnit XML stores paths as dot-separated classnames and a separate name
    attribute.  This function reconstructs the canonical pytest node ID
    ``path/to/test_file.py::test_function`` so that matching is exact —
    a same-named function in a different file will NOT produce the same key.

    For a JUnit case produced by pytest the classname is the Python module
    path (e.g. ``tests.regression.test_rc001_foo``) and the name is the
    test-function name (e.g. ``test_leading_zero_invoice_no_preserved``).
    The canonical node ID is reconstructed as
    ``tests/regression/test_rc001_foo.py::test_leading_zero_invoice_no_preserved``.
    """
    lookup: dict[str, str] = {}
    for c in cases:
        classname = c.get("classname", "")
        name = c.get("name", "")
        # Convert dot-separated module path to file path and append .py
        file_path = classname.replace(".", "/") + ".py"
        node_id = f"{file_path}::{name}"
        lookup[node_id] = c["status"]
    return lookup
