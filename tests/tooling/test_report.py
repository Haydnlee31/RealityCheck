"""
Tooling tests for realitycheck.report.

Uses a small synthetic evidence record (clearly labelled test data) to
verify the report contains all expected evidence-chain sections.

This synthetic record is NOT project evidence and is NOT written under runs/.
"""

from realitycheck.report import generate_report

# ---------------------------------------------------------------------------
# Synthetic test evidence record
# ---------------------------------------------------------------------------

SYNTHETIC_EVIDENCE = {
    "schema_version": "1.0",
    "run_id": "tooling-test-run",
    "finding_id": "tooling-finding-001",
    "requirement": {
        "id": "AC-TEST",
        "text": "The application must preserve the identifier unchanged.",
        "classification": "documented",
        "sources": [
            {
                "kind": "application-contract",
                "artifact": "docs/application-contract.md",
                "locator": "AC-001",
                "excerpt": "invoice_no is an opaque string identifier",
            },
            {
                "kind": "publisher-documentation",
                "artifact": "UCI Online Retail dataset documentation",
                "locator": None,
                "excerpt": None,
            },
        ],
    },
    "assumption": {
        "description": "The implementation coerces invoice_no through int().",
        "code_artifact": "sample_app/importer.py",
        "symbol": "_normalize",
    },
    "counterexample": {
        "kind": "input-record",
        "fixture": "fixtures/regression.jsonl",
        "record_ids": ["reg-001"],
        "expected_behavior": "Stored invoice_no equals the input string byte-for-byte.",
    },
    "acceptance": {
        "decision": "accepted",
        "reviewer": "developer@example.com",
        "timestamp": "2025-01-15T10:00:00+00:00",
        "protected_manifest": "runs/tooling-test-run/protected-manifest.json",
    },
    "regression": {
        "test_artifact": "tests/regression/test_invoice_preservation.py",
        "node_ids": ["tests/regression/test_invoice_preservation.py::test_alphanumeric_invoice_preserved"],
        "expected_failure": "AssertionError: stored invoice_no 'C536365' != expected 'C536365'",
    },
    "executions": {
        "reproduction": {
            "execution_id": "repro-exec-001",
            "phase": "reproduction",
            "outcome": "failed",
            "artifact_dir": "runs/tooling-test-run/repro-exec-001",
        },
        "verification": {
            "execution_id": "verif-exec-001",
            "phase": "verification",
            "outcome": "passed",
            "artifact_dir": "runs/tooling-test-run/verif-exec-001",
        },
    },
    "repair": {
        "base_snapshot": "aabbcc001",
        "candidate_snapshot": "ddeeff002",
        "patch": "--- a/sample_app/importer.py\n+++ b/sample_app/importer.py\n@@ -1 +1 @@\n-normalized = str(int(...))\n+normalized = str(...)",
    },
    "verdict": {
        "status": "verified_for_tested_scenarios",
        "reason": "Verification execution passed all required tests",
        "limitations": [
            "Verdict covers only the tested scenarios — not all contract requirements."
        ],
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_report_contains_requirement_section():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Requirement" in md
    assert "AC-TEST" in md
    assert "documented" in md


def test_report_contains_sources():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "application-contract" in md
    assert "docs/application-contract.md" in md
    assert "AC-001" in md


def test_report_contains_assumption_section():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Implementation Assumption" in md
    assert "int()" in md
    assert "sample_app/importer.py" in md


def test_report_contains_counterexample_section():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Counterexample" in md
    assert "reg-001" in md
    assert "byte-for-byte" in md


def test_report_contains_acceptance_section():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Developer Acceptance" in md
    assert "accepted" in md
    assert "developer@example.com" in md


def test_report_contains_regression_section():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Regression Test" in md
    assert "test_invoice_preservation" in md


def test_report_contains_execution_sections():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Reproduction Execution" in md
    assert "Verification Execution" in md


def test_report_contains_repair_section():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Repair" in md
    assert "aabbcc001" in md
    assert "ddeeff002" in md


def test_report_contains_verdict_section():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "Verdict" in md
    assert "verified_for_tested_scenarios" in md
    assert "Limitations" in md


def test_report_null_repair_handled():
    evidence = dict(SYNTHETIC_EVIDENCE)
    evidence = {**evidence, "repair": None}
    md = generate_report(evidence)
    assert "No repair recorded" in md


def test_report_distinguishes_model_vs_deterministic():
    """Report must label model-authored sections and execution result sections."""
    md = generate_report(SYNTHETIC_EVIDENCE)
    # Model-authored labels
    assert "Model" in md or "model" in md
    # Deterministic execution label
    assert "deterministic" in md or "Deterministic" in md


def test_report_run_and_finding_ids_present():
    md = generate_report(SYNTHETIC_EVIDENCE)
    assert "tooling-test-run" in md
    assert "tooling-finding-001" in md
