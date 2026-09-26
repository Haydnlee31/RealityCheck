"""
RealityCheck evidence-chain report generator.

Produces a Markdown document from a completed evidence JSON record.

The report clearly distinguishes:

    Model interpretation / finding information
vs.
    Observed deterministic execution results

No LLM is called here.  All content comes from the evidence record passed in
and from on-disk execution.json files referenced via artifact_dir.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _heading(level: int, text: str) -> str:
    return f"{'#' * level} {text}\n"


def _field(label: str, value: Any) -> str:
    if value is None:
        value = "_not recorded_"
    return f"**{label}:** {value}  \n"


def _code_block(content: str, lang: str = "") -> str:
    return f"```{lang}\n{content}\n```\n"


def _load_execution_detail(
    exec_rec: dict[str, Any], repo_root: str | Path | None = None
) -> dict[str, Any]:
    """Return the full execution.json for *exec_rec*, merging over the stub.

    The evidence record stores a minimal stub
    ``{execution_id, phase, outcome, artifact_dir}``.  The full detail lives in
    ``<artifact_dir>/execution.json``.  When that file is present and readable
    we merge it on top of the stub so callers always get the richest available
    data regardless of whether the evidence was serialised with full or stub
    fields.
    """
    if not exec_rec:
        return {}

    artifact_dir = exec_rec.get("artifact_dir")
    if not artifact_dir:
        return dict(exec_rec)

    candidate = Path(artifact_dir) / "execution.json"
    if repo_root is not None:
        candidate_rooted = Path(repo_root) / candidate
        if candidate_rooted.exists():
            candidate = candidate_rooted

    if candidate.exists():
        try:
            with candidate.open() as fh:
                on_disk = json.load(fh)
            merged = dict(exec_rec)
            merged.update(on_disk)
            return merged
        except Exception:
            pass

    return dict(exec_rec)


def _protected_manifest_badge(pm: dict[str, Any] | None) -> str:
    """Return a short inline badge string for a protected-manifest result."""
    if pm is None:
        return "_not recorded_"
    ok = pm.get("ok")
    if ok is True:
        return "✓ verified — all protected files present and unmodified"
    missing = pm.get("missing", [])
    modified = pm.get("modified", [])
    parts = []
    if missing:
        parts.append(f"{len(missing)} missing")
    if modified:
        parts.append(f"{len(modified)} modified")
    detail = ", ".join(parts) or "unknown failure"
    return f"✗ FAILED ({detail})"


def _execution_section(
    exec_rec: dict[str, Any],
    title: str,
    repo_root: str | Path | None = None,
) -> str:
    """Render one execution section with full detail loaded from disk."""
    if not exec_rec:
        return f"_{title}: not recorded_\n\n"

    detail = _load_execution_detail(exec_rec, repo_root=repo_root)

    lines = [_heading(3, title)]

    # ── Deterministic observations header ──────────────────────────────────
    lines.append(
        "> _Deterministic observation — values recorded by the runner, "
        "not inferred by the model._\n\n"
    )

    lines.append(_field("Execution ID", f"`{detail.get('execution_id')}`"))
    lines.append(_field("Phase", detail.get("phase")))
    lines.append(_field("Started at", detail.get("started_at")))
    lines.append(_field("Duration (ms)", detail.get("duration_ms")))
    lines.append(_field("Exit code", detail.get("exit_code")))
    lines.append(_field("Outcome", f"**{detail.get('outcome', '_not recorded_')}**"))

    targets = detail.get("pytest_targets") or []
    if targets:
        lines.append(_field("Pytest targets", ", ".join(f"`{t}`" for t in targets)))
    else:
        lines.append(_field("Pytest targets", "_not recorded_"))

    snap = detail.get("application_snapshot")
    lines.append(_field("Application snapshot", f"`{snap}`" if snap else "_not recorded_"))

    # ── Protected-manifest status ───────────────────────────────────────────
    pm = detail.get("protected_manifest")
    pm_badge = _protected_manifest_badge(pm)
    lines.append(_field("Protected-manifest verification", pm_badge))
    if pm and not pm.get("ok"):
        for path in pm.get("missing", []):
            lines.append(f"  - missing: `{path}`  \n")
        for path in pm.get("modified", []):
            lines.append(f"  - modified: `{path}`  \n")

    # ── Test results ────────────────────────────────────────────────────────
    sr = detail.get("structured_results") or {}
    if sr and not sr.get("parse_error"):
        lines.append(
            _field(
                "Test counts",
                f"tests={sr.get('tests', '?')}  "
                f"failures={sr.get('failures', '?')}  "
                f"errors={sr.get('errors', '?')}  "
                f"skipped={sr.get('skipped', '?')}",
            )
        )
        cases = sr.get("cases") or []
        if cases:
            lines.append("\n**Individual test results:**\n\n")
            lines.append("| Status | Test | Time (s) |\n|--------|------|----------|\n")
            for c in cases:
                icon = {"passed": "✓", "failed": "✗", "error": "!", "skipped": "–"}.get(
                    c.get("status", ""), "?"
                )
                status = c.get("status", "?")
                name = f"{c.get('classname', '')}.{c.get('name', '')}"
                t = c.get("time", "")
                lines.append(f"| {icon} {status} | `{name}` | {t} |\n")
            lines.append("\n")
    elif sr.get("parse_error"):
        lines.append(_field("JUnit parse error", sr["parse_error"]))

    return "\n".join(lines)


def generate_report(
    evidence: dict[str, Any],
    repo_root: str | Path | None = None,
) -> str:
    """Return a Markdown string representing the full evidence chain.

    Parameters
    ----------
    evidence:
        A dict conforming to the RealityCheck evidence schema.
    repo_root:
        Optional path to the repository root, used to resolve
        ``artifact_dir`` references when loading execution detail files.
        When *None* the current working directory is used.

    Returns
    -------
    A self-contained Markdown document.
    """
    if repo_root is None:
        repo_root = Path(os.getcwd())

    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────
    run_id = evidence.get("run_id", "_unknown_")
    finding_id = evidence.get("finding_id", "_unknown_")
    schema_version = evidence.get("schema_version", "_unknown_")

    lines.append(_heading(1, "RealityCheck Evidence Report"))
    lines.append(f"**Run:** `{run_id}`  \n")
    lines.append(f"**Finding:** `{finding_id}`  \n")
    lines.append(f"**Schema version:** `{schema_version}`  \n")
    lines.append("\n---\n")

    # ── Legend ────────────────────────────────────────────────────────────
    lines.append(_heading(2, "Legend"))
    lines.append(
        "This report distinguishes two kinds of content:\n\n"
        "- **Model interpretation** — requirement analysis, implementation assumption, "
        "counterexample, and proposed relationship between code and contract. "
        "These are model-authored and were reviewed by a developer before acceptance.\n"
        "- **Deterministic observation** — execution IDs, exit codes, "
        "pass/fail/error/timeout, protected-manifest hashes, and application snapshot IDs. "
        "These are recorded by the deterministic `realitycheck.runner` tooling; "
        "no LLM judgment is applied.\n\n"
    )
    lines.append("\n---\n")

    # ── Requirement ── MODEL INTERPRETATION ───────────────────────────────
    lines.append(_heading(2, "Requirement _(model interpretation)_"))
    req = evidence.get("requirement") or {}
    lines.append(
        "> **Model interpretation** — requirement identified and classified by the model. "
        "Sources are cited verbatim from the referenced documents.\n\n"
    )
    lines.append(_field("ID", req.get("id")))
    lines.append(_field("Classification", req.get("classification")))
    lines.append(f"\n{req.get('text', '_not recorded_')}\n\n")
    sources = req.get("sources") or []
    if sources:
        lines.append(_heading(3, "Sources"))
        for src in sources:
            kind = src.get("kind", "unknown")
            artifact = src.get("artifact", "")
            locator = src.get("locator", "")
            excerpt = src.get("excerpt", "")
            lines.append(f"- **{kind}** — `{artifact}`")
            if locator:
                lines.append(f" @ `{locator}`")
            lines.append("  \n")
            if excerpt:
                lines.append(f"  > {excerpt}  \n")
        lines.append("\n")
    lines.append("\n---\n")

    # ── Implementation assumption ── MODEL INTERPRETATION ─────────────────
    lines.append(_heading(2, "Implementation Assumption _(model interpretation)_"))
    lines.append(
        "> **Model interpretation** — how the model assessed the implementation as diverging "
        "from the requirement. Reviewed and accepted by the developer before any repair.\n\n"
    )
    assumption = evidence.get("assumption") or {}
    lines.append(f"{assumption.get('description', '_not recorded_')}\n\n")
    if assumption.get("code_artifact"):
        lines.append(_field("Code artifact", f"`{assumption['code_artifact']}`"))
    if assumption.get("symbol"):
        lines.append(_field("Symbol", f"`{assumption['symbol']}`"))
    lines.append("\n---\n")

    # ── Counterexample ── MODEL INTERPRETATION ────────────────────────────
    lines.append(_heading(2, "Counterexample _(model interpretation)_"))
    lines.append(
        "> **Model interpretation** — minimal input the model identified as exercising the "
        "mismatch. Developer-accepted before the regression test was written.\n\n"
    )
    ce = evidence.get("counterexample") or {}
    lines.append(_field("Kind", ce.get("kind")))
    lines.append(_field("Fixture", ce.get("fixture")))
    ids = ce.get("record_ids") or []
    if ids:
        lines.append(_field("Record IDs", ", ".join(ids)))
    lines.append(
        f"\n**Expected behavior:**  \n{ce.get('expected_behavior', '_not recorded_')}\n\n"
    )
    lines.append("\n---\n")

    # ── Developer acceptance ───────────────────────────────────────────────
    lines.append(_heading(2, "Developer Acceptance"))
    lines.append(
        "> _This section records an explicit human decision. "
        "The workflow does not proceed past this point without ACCEPT._\n\n"
    )
    acc = evidence.get("acceptance") or {}
    lines.append(_field("Decision", acc.get("decision")))
    lines.append(_field("Reviewer", acc.get("reviewer")))
    lines.append(_field("Timestamp", acc.get("timestamp")))
    lines.append(_field("Protected manifest", acc.get("protected_manifest")))
    lines.append("\n---\n")

    # ── Regression test ───────────────────────────────────────────────────
    lines.append(_heading(2, "Regression Test"))
    lines.append(
        "> _Accepted regression test artifact — must not be modified after acceptance._\n\n"
    )
    reg = evidence.get("regression") or {}
    lines.append(_field("Test artifact", reg.get("test_artifact")))
    node_ids = reg.get("node_ids") or []
    if node_ids:
        lines.append(_field("Node IDs", ", ".join(f"`{n}`" for n in node_ids)))
    lines.append(_field("Expected failure (on unrepaired app)", reg.get("expected_failure")))
    lines.append("\n---\n")

    # ── Protected-manifest verification summary ── DETERMINISTIC ──────────
    lines.append(_heading(2, "Protected-Manifest Verification _(deterministic observations)_"))
    lines.append(
        "> **Deterministic observation** — hash verification performed by the runner at each "
        "execution phase. A FAILED status immediately blocks the verdict.\n\n"
    )

    executions = evidence.get("executions") or {}
    reproduction_stub = executions.get("reproduction") or {}
    verification_stub = executions.get("verification") or {}
    baseline_stub = executions.get("baseline") or {}

    repro_detail = _load_execution_detail(reproduction_stub, repo_root=repo_root)
    verif_detail = _load_execution_detail(verification_stub, repo_root=repo_root)
    base_detail = _load_execution_detail(baseline_stub, repo_root=repo_root)

    lines.append("| Phase | Execution ID | Status | Changed/Missing |\n")
    lines.append("|-------|-------------|--------|------------------|\n")

    for label, detail in [
        ("Reproduction", repro_detail),
        ("Verification (regression)", verif_detail),
        ("Verification (baseline)", base_detail),
    ]:
        if not detail:
            lines.append(f"| {label} | — | _not recorded_ | — |\n")
            continue
        eid = detail.get("execution_id", "—")
        pm = detail.get("protected_manifest")
        if pm is None:
            status_cell = "_not recorded_"
            changes_cell = "—"
        elif pm.get("ok"):
            status_cell = "✓ verified"
            changes_cell = "—"
        else:
            status_cell = "✗ FAILED"
            missing = pm.get("missing", [])
            modified = pm.get("modified", [])
            parts = [f"missing: `{p}`" for p in missing] + [
                f"modified: `{p}`" for p in modified
            ]
            changes_cell = "; ".join(parts) if parts else "unknown"
        lines.append(f"| {label} | `{eid}` | {status_cell} | {changes_cell} |\n")

    lines.append("\n")
    lines.append("\n---\n")

    # ── Execution results ── DETERMINISTIC ────────────────────────────────
    lines.append(_heading(2, "Execution Results _(deterministic observations)_"))
    lines.append(
        "> **Deterministic observation** — all execution outcomes below are recorded by the "
        "runner. No LLM judgment is applied to determine pass or fail.\n\n"
    )

    lines.append(
        _execution_section(reproduction_stub, "Reproduction Execution", repo_root=repo_root)
    )
    lines.append("\n")
    lines.append(
        _execution_section(
            verification_stub,
            "Verification Execution — Regression Test",
            repo_root=repo_root,
        )
    )
    lines.append("\n")
    lines.append(
        _execution_section(
            baseline_stub,
            "Verification Execution — Baseline Preservation",
            repo_root=repo_root,
        )
    )
    lines.append("\n---\n")

    # ── Repair ────────────────────────────────────────────────────────────
    lines.append(_heading(2, "Repair"))
    repair = evidence.get("repair")
    if not repair:
        lines.append("_No repair recorded._\n")
    else:
        lines.append(
            "> **Deterministic observation** — snapshots are SHA-256 digests of the "
            "application directory tree computed by the runner.\n\n"
        )
        lines.append(_field("Base snapshot (pre-repair)", f"`{repair.get('base_snapshot')}`"))
        lines.append(
            _field("Candidate snapshot (post-repair)", f"`{repair.get('candidate_snapshot')}`")
        )
        patch = repair.get("patch")
        if patch:
            lines.append("\n**Patch:**\n\n")
            lines.append(_code_block(patch, "diff"))
    lines.append("\n---\n")

    # ── Verdict ── DETERMINISTIC ──────────────────────────────────────────
    lines.append(_heading(2, "Verdict _(deterministic observation)_"))
    lines.append(
        "> **Deterministic observation** — verdict derived from execution records by "
        "`realitycheck.runner.compute_verdict`. Not a model-generated assessment.\n\n"
    )
    verdict = evidence.get("verdict") or {}
    status = verdict.get("status", "_not recorded_")
    lines.append(_field("Status", f"**{status}**"))
    lines.append(_field("Reason", verdict.get("reason")))
    limitations = verdict.get("limitations") or []
    if limitations:
        lines.append("\n**Limitations:**\n\n")
        for lim in limitations:
            lines.append(f"- {lim}\n")
    lines.append("\n")

    return "".join(lines)
