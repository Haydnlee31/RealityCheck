"""
RealityCheck evidence-chain report generator.

Produces a Markdown document from a completed evidence JSON record.

The report clearly distinguishes:

    Model interpretation / finding information
vs.
    Observed deterministic execution results

No LLM is called here.  All content comes from the evidence record passed in.
"""

from __future__ import annotations

from typing import Any


def _heading(level: int, text: str) -> str:
    return f"{'#' * level} {text}\n"


def _field(label: str, value: Any) -> str:
    if value is None:
        value = "_not recorded_"
    return f"**{label}:** {value}  \n"


def _code_block(content: str, lang: str = "") -> str:
    return f"```{lang}\n{content}\n```\n"


def _execution_section(exec_rec: dict[str, Any], title: str) -> str:
    if not exec_rec:
        return f"_{title}: not recorded_\n\n"
    lines = [_heading(3, title)]
    lines.append(_field("Phase", exec_rec.get("phase")))
    lines.append(_field("Outcome", exec_rec.get("outcome")))
    lines.append(_field("Exit code", exec_rec.get("exit_code")))
    lines.append(_field("Duration (ms)", exec_rec.get("duration_ms")))
    lines.append(_field("Started at", exec_rec.get("started_at")))
    lines.append(_field("Pytest targets", ", ".join(exec_rec.get("pytest_targets", []))))
    lines.append(_field("Application snapshot", exec_rec.get("application_snapshot")))

    pm = exec_rec.get("protected_manifest")
    if pm is not None:
        ok = pm.get("ok")
        pm_label = "✓ verified" if ok else "✗ FAILED"
        lines.append(_field("Protected manifest", pm_label))
        if not ok:
            for missing in pm.get("missing", []):
                lines.append(f"  - missing: `{missing}`  \n")
            for modified in pm.get("modified", []):
                lines.append(f"  - modified: `{modified}`  \n")

    sr = exec_rec.get("structured_results", {})
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
        cases = sr.get("cases", [])
        if cases:
            lines.append("\n**Individual test results:**\n\n")
            lines.append("| Status | Test |\n|--------|------|\n")
            for c in cases:
                icon = {"passed": "✓", "failed": "✗", "error": "!", "skipped": "–"}.get(
                    c["status"], "?"
                )
                name = f"{c.get('classname', '')}.{c.get('name', '')}"
                lines.append(f"| {icon} {c['status']} | `{name}` |\n")
            lines.append("\n")
    elif sr.get("parse_error"):
        lines.append(_field("JUnit parse error", sr["parse_error"]))

    return "\n".join(lines)


def generate_report(evidence: dict[str, Any]) -> str:
    """Return a Markdown string representing the full evidence chain.

    Parameters
    ----------
    evidence:
        A dict conforming to the RealityCheck evidence schema.

    Returns
    -------
    A self-contained Markdown document.
    """
    lines: list[str] = []

    # --- Header ---
    run_id = evidence.get("run_id", "_unknown_")
    finding_id = evidence.get("finding_id", "_unknown_")
    schema_version = evidence.get("schema_version", "_unknown_")

    lines.append(_heading(1, f"RealityCheck Evidence Report"))
    lines.append(f"**Run:** `{run_id}`  \n")
    lines.append(f"**Finding:** `{finding_id}`  \n")
    lines.append(f"**Schema version:** `{schema_version}`  \n")
    lines.append("\n---\n")

    # --- Requirement ---
    lines.append(_heading(2, "Requirement"))
    req = evidence.get("requirement") or {}
    lines.append(
        "> _The following requirement was identified by investigation. "
        "Classification and sources are model-authored unless marked otherwise._\n\n"
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

    # --- Assumption ---
    lines.append(_heading(2, "Implementation Assumption"))
    lines.append(
        "> _Model-authored interpretation of how the implementation diverges from the requirement._\n\n"
    )
    assumption = evidence.get("assumption") or {}
    lines.append(f"{assumption.get('description', '_not recorded_')}\n\n")
    if assumption.get("code_artifact"):
        lines.append(_field("Code artifact", f"`{assumption['code_artifact']}`"))
    if assumption.get("symbol"):
        lines.append(_field("Symbol", f"`{assumption['symbol']}`"))
    lines.append("\n---\n")

    # --- Counterexample ---
    lines.append(_heading(2, "Counterexample"))
    lines.append(
        "> _Model-authored counterexample demonstrating the divergence._\n\n"
    )
    ce = evidence.get("counterexample") or {}
    lines.append(_field("Kind", ce.get("kind")))
    lines.append(_field("Fixture", ce.get("fixture")))
    ids = ce.get("record_ids") or []
    if ids:
        lines.append(_field("Record IDs", ", ".join(ids)))
    lines.append(f"\n**Expected behavior:**  \n{ce.get('expected_behavior', '_not recorded_')}\n\n")
    lines.append("\n---\n")

    # --- Developer acceptance ---
    lines.append(_heading(2, "Developer Acceptance"))
    lines.append(
        "> _This section is completed by a human developer, not the model._\n\n"
    )
    acc = evidence.get("acceptance") or {}
    lines.append(_field("Decision", acc.get("decision")))
    lines.append(_field("Reviewer", acc.get("reviewer")))
    lines.append(_field("Timestamp", acc.get("timestamp")))
    lines.append(_field("Protected manifest", acc.get("protected_manifest")))
    lines.append("\n---\n")

    # --- Regression test ---
    lines.append(_heading(2, "Regression Test"))
    lines.append(
        "> _Accepted regression test artifact — must not be modified after acceptance._\n\n"
    )
    reg = evidence.get("regression") or {}
    lines.append(_field("Test artifact", reg.get("test_artifact")))
    node_ids = reg.get("node_ids") or []
    if node_ids:
        lines.append(_field("Node IDs", ", ".join(f"`{n}`" for n in node_ids)))
    lines.append(_field("Expected failure", reg.get("expected_failure")))
    lines.append("\n---\n")

    # --- Executions ---
    lines.append(_heading(2, "Execution Results"))
    lines.append(
        "> _All execution outcomes below are deterministic records from the runner. "
        "No LLM judgment is applied._\n\n"
    )
    executions = evidence.get("executions") or {}
    reproduction = executions.get("reproduction") or {}
    verification = executions.get("verification") or {}

    lines.append(_execution_section(reproduction, "Reproduction Execution"))
    lines.append("\n")
    lines.append(_execution_section(verification, "Verification Execution"))
    lines.append("\n---\n")

    # --- Repair ---
    lines.append(_heading(2, "Repair"))
    repair = evidence.get("repair")
    if not repair:
        lines.append("_No repair recorded._\n")
    else:
        lines.append(_field("Base snapshot", repair.get("base_snapshot")))
        lines.append(_field("Candidate snapshot", repair.get("candidate_snapshot")))
        patch = repair.get("patch")
        if patch:
            lines.append("\n**Patch:**\n\n")
            lines.append(_code_block(patch, "diff"))
    lines.append("\n---\n")

    # --- Verdict ---
    lines.append(_heading(2, "Verdict"))
    lines.append(
        "> _Deterministic verdict derived from execution records. "
        "Not a model-generated assessment._\n\n"
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
