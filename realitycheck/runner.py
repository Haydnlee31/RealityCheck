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
) -> dict[str, Any]:
    """Compute a deterministic verdict.

    Parameters
    ----------
    reproduction_execution:
        The execution record from the reproduction phase.
    verification_execution:
        The execution record from the verification phase.
    protected_verification:
        The result of ``verify_protected_manifest`` called immediately before
        or during the verification execution.  Pass ``None`` if the protected
        manifest has not been created yet.

    Returns
    -------
    ``{"status": str, "reason": str, "limitations": list[str]}``
    """
    limitations: list[str] = []
    sr = verification_execution.get("structured_results", {})

    # --- hard blocks ---
    if protected_verification is not None and not protected_verification.get("ok"):
        missing = protected_verification.get("missing", [])
        modified = protected_verification.get("modified", [])
        parts = []
        if missing:
            parts.append(f"missing: {missing}")
        if modified:
            parts.append(f"modified: {modified}")
        return {
            "status": "blocked",
            "reason": f"Protected input verification failed — {'; '.join(parts)}",
            "limitations": limitations,
        }

    if verification_execution["outcome"] == "timeout":
        return {
            "status": "blocked",
            "reason": "Verification execution timed out",
            "limitations": limitations,
        }

    if verification_execution["outcome"] == "error":
        return {
            "status": "blocked",
            "reason": f"Verification execution exited with error (exit code {verification_execution['exit_code']})",
            "limitations": limitations,
        }

    # pytest collection failure shows up as exit code 4 (no tests collected)
    if sr.get("tests", 0) == 0 and not sr.get("parse_error"):
        return {
            "status": "blocked",
            "reason": "No tests were collected during verification",
            "limitations": limitations,
        }

    if sr.get("skipped", 0) > 0 and sr.get("tests", 0) - sr.get("skipped", 0) == 0:
        return {
            "status": "blocked",
            "reason": "All required verification tests were skipped",
            "limitations": limitations,
        }

    # --- reproduction must have failed ---
    if reproduction_execution["outcome"] not in ("failed", "error"):
        limitations.append(
            "Reproduction phase did not produce a failure; "
            "counterexample may not exercise the defect."
        )

    # --- final verdict ---
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
