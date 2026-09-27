// Generated from repository records by tools/export_evidence.py.
window.RC_EVIDENCE = {
  "sourceCommit": "b6f64bb800d0ff2ff4118382c8ce32f7d2217db5",
  "findings": [
    {
      "id": "RC-001",
      "requirement": "AC-001",
      "acceptedAt": "2026-09-26T08:42:00+00:00",
      "evidence": "evidence/runs/rc-001/evidence.json",
      "report": "evidence/runs/rc-001/report-v2.md",
      "manifest": "evidence/runs/rc-001/protected-manifest.json",
      "executions": {
        "reproduction": {
          "record": {
            "execution_id": "df96ba74-10dd-4505-87e7-b7136736d835",
            "phase": "reproduction",
            "started_at": "2026-09-26T08:42:48.127541+00:00",
            "duration_ms": 547,
            "exit_code": 1,
            "outcome": "failed",
            "pytest_targets": [
              "tests/regression/test_rc001_invoice_no_preservation.py::test_leading_zero_invoice_no_preserved"
            ],
            "application_snapshot": "3e7416b56e789479b88372315cba35b816da91b4906dd64c2509b04a0e8ef87b",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-001/df96ba74-10dd-4505-87e7-b7136736d835/environment.json",
            "stdout": "runs/rc-001/df96ba74-10dd-4505-87e7-b7136736d835/stdout.txt",
            "stderr": "runs/rc-001/df96ba74-10dd-4505-87e7-b7136736d835/stderr.txt",
            "structured_results": {
              "tests": 1,
              "failures": 1,
              "errors": 0,
              "skipped": 0,
              "time": "0.025",
              "cases": [
                {
                  "classname": "tests.regression.test_rc001_invoice_no_preservation",
                  "name": "test_leading_zero_invoice_no_preserved",
                  "status": "failed",
                  "time": "0.002"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-001/df96ba74-10dd-4505-87e7-b7136736d835/execution.json",
          "junit": "evidence/runs/rc-001/df96ba74-10dd-4505-87e7-b7136736d835/junit.xml",
          "stdout": "evidence/runs/rc-001/df96ba74-10dd-4505-87e7-b7136736d835/stdout.txt"
        },
        "verification": {
          "record": {
            "execution_id": "5fb09aa4-2f09-4ff5-83ef-ca717c023f6b",
            "phase": "verification",
            "started_at": "2026-09-26T08:46:09.820822+00:00",
            "duration_ms": 437,
            "exit_code": 0,
            "outcome": "passed",
            "pytest_targets": [
              "tests/regression/test_rc001_invoice_no_preservation.py::test_leading_zero_invoice_no_preserved"
            ],
            "application_snapshot": "a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-001/5fb09aa4-2f09-4ff5-83ef-ca717c023f6b/environment.json",
            "stdout": "runs/rc-001/5fb09aa4-2f09-4ff5-83ef-ca717c023f6b/stdout.txt",
            "stderr": "runs/rc-001/5fb09aa4-2f09-4ff5-83ef-ca717c023f6b/stderr.txt",
            "structured_results": {
              "tests": 1,
              "failures": 0,
              "errors": 0,
              "skipped": 0,
              "time": "0.014",
              "cases": [
                {
                  "classname": "tests.regression.test_rc001_invoice_no_preservation",
                  "name": "test_leading_zero_invoice_no_preserved",
                  "status": "passed",
                  "time": "0.002"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-001/5fb09aa4-2f09-4ff5-83ef-ca717c023f6b/execution.json",
          "junit": "evidence/runs/rc-001/5fb09aa4-2f09-4ff5-83ef-ca717c023f6b/junit.xml",
          "stdout": "evidence/runs/rc-001/5fb09aa4-2f09-4ff5-83ef-ca717c023f6b/stdout.txt"
        },
        "baseline": {
          "record": {
            "execution_id": "fae0e1d9-b45a-475c-8dbc-e384fcdd32e6",
            "phase": "verification",
            "started_at": "2026-09-26T08:46:10.259731+00:00",
            "duration_ms": 286,
            "exit_code": 0,
            "outcome": "passed",
            "pytest_targets": [
              "tests/existing"
            ],
            "application_snapshot": "a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-001/fae0e1d9-b45a-475c-8dbc-e384fcdd32e6/environment.json",
            "stdout": "runs/rc-001/fae0e1d9-b45a-475c-8dbc-e384fcdd32e6/stdout.txt",
            "stderr": "runs/rc-001/fae0e1d9-b45a-475c-8dbc-e384fcdd32e6/stderr.txt",
            "structured_results": {
              "tests": 5,
              "failures": 0,
              "errors": 0,
              "skipped": 0,
              "time": "0.018",
              "cases": [
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_single_line_item_import",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_stored_contents_retrievable",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_multiple_line_items_same_invoice",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_stored_invoice_identifiers_match_expected",
                  "status": "passed",
                  "time": "0.002"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_lookup_returns_only_matching_invoice",
                  "status": "passed",
                  "time": "0.003"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-001/fae0e1d9-b45a-475c-8dbc-e384fcdd32e6/execution.json",
          "junit": "evidence/runs/rc-001/fae0e1d9-b45a-475c-8dbc-e384fcdd32e6/junit.xml",
          "stdout": "evidence/runs/rc-001/fae0e1d9-b45a-475c-8dbc-e384fcdd32e6/stdout.txt"
        }
      }
    },
    {
      "id": "RC-002",
      "requirement": "AC-007",
      "acceptedAt": "2026-09-26T10:00:00+00:00",
      "evidence": "evidence/runs/rc-002/evidence-rc002.json",
      "report": "evidence/runs/rc-002/report-rc-002.md",
      "manifest": "evidence/runs/rc-002/protected-manifest.json",
      "executions": {
        "reproduction": {
          "record": {
            "execution_id": "07b5f2b6-5034-4d48-ae44-6b0f761a696e",
            "phase": "reproduction",
            "started_at": "2026-09-26T10:05:10.192639+00:00",
            "duration_ms": 470,
            "exit_code": 1,
            "outcome": "failed",
            "pytest_targets": [
              "tests/regression/test_rc002_batch_atomicity.py::test_failed_batch_leaves_no_partial_rows"
            ],
            "application_snapshot": "a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-002/07b5f2b6-5034-4d48-ae44-6b0f761a696e/environment.json",
            "stdout": "runs/rc-002/07b5f2b6-5034-4d48-ae44-6b0f761a696e/stdout.txt",
            "stderr": "runs/rc-002/07b5f2b6-5034-4d48-ae44-6b0f761a696e/stderr.txt",
            "structured_results": {
              "tests": 1,
              "failures": 1,
              "errors": 0,
              "skipped": 0,
              "time": "0.026",
              "cases": [
                {
                  "classname": "tests.regression.test_rc002_batch_atomicity",
                  "name": "test_failed_batch_leaves_no_partial_rows",
                  "status": "failed",
                  "time": "0.003"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-002/07b5f2b6-5034-4d48-ae44-6b0f761a696e/execution.json",
          "junit": "evidence/runs/rc-002/07b5f2b6-5034-4d48-ae44-6b0f761a696e/junit.xml",
          "stdout": "evidence/runs/rc-002/07b5f2b6-5034-4d48-ae44-6b0f761a696e/stdout.txt"
        },
        "verification": {
          "record": {
            "execution_id": "2bc00fd9-68ae-4246-ad39-4f94dfefd59f",
            "phase": "verification",
            "started_at": "2026-09-26T10:09:02.214833+00:00",
            "duration_ms": 430,
            "exit_code": 0,
            "outcome": "passed",
            "pytest_targets": [
              "tests/regression/test_rc002_batch_atomicity.py::test_failed_batch_leaves_no_partial_rows"
            ],
            "application_snapshot": "a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-002/2bc00fd9-68ae-4246-ad39-4f94dfefd59f/environment.json",
            "stdout": "runs/rc-002/2bc00fd9-68ae-4246-ad39-4f94dfefd59f/stdout.txt",
            "stderr": "runs/rc-002/2bc00fd9-68ae-4246-ad39-4f94dfefd59f/stderr.txt",
            "structured_results": {
              "tests": 1,
              "failures": 0,
              "errors": 0,
              "skipped": 0,
              "time": "0.012",
              "cases": [
                {
                  "classname": "tests.regression.test_rc002_batch_atomicity",
                  "name": "test_failed_batch_leaves_no_partial_rows",
                  "status": "passed",
                  "time": "0.002"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-002/2bc00fd9-68ae-4246-ad39-4f94dfefd59f/execution.json",
          "junit": "evidence/runs/rc-002/2bc00fd9-68ae-4246-ad39-4f94dfefd59f/junit.xml",
          "stdout": "evidence/runs/rc-002/2bc00fd9-68ae-4246-ad39-4f94dfefd59f/stdout.txt"
        },
        "baseline": {
          "record": {
            "execution_id": "81715fe2-3ecd-4047-90ff-fba8c105b325",
            "phase": "verification",
            "started_at": "2026-09-26T10:09:39.915986+00:00",
            "duration_ms": 297,
            "exit_code": 0,
            "outcome": "passed",
            "pytest_targets": [
              "tests/existing"
            ],
            "application_snapshot": "a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/environment.json",
            "stdout": "runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/stdout.txt",
            "stderr": "runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/stderr.txt",
            "structured_results": {
              "tests": 5,
              "failures": 0,
              "errors": 0,
              "skipped": 0,
              "time": "0.016",
              "cases": [
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_single_line_item_import",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_stored_contents_retrievable",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_multiple_line_items_same_invoice",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_stored_invoice_identifiers_match_expected",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_lookup_returns_only_matching_invoice",
                  "status": "passed",
                  "time": "0.001"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/execution.json",
          "junit": "evidence/runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/junit.xml",
          "stdout": "evidence/runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/stdout.txt"
        }
      }
    },
    {
      "id": "RC-003",
      "requirement": "AC-004 / AC-005 / AC-006",
      "acceptedAt": "2026-09-26T10:00:00+00:00",
      "evidence": "evidence/runs/rc-002/evidence-rc003.json",
      "report": "evidence/runs/rc-002/report-rc-003.md",
      "manifest": "evidence/runs/rc-002/protected-manifest.json",
      "executions": {
        "reproduction": {
          "record": {
            "execution_id": "7de07b54-693f-4d45-a422-e42ea3cd543a",
            "phase": "reproduction",
            "started_at": "2026-09-26T10:05:37.859236+00:00",
            "duration_ms": 394,
            "exit_code": 1,
            "outcome": "failed",
            "pytest_targets": [
              "tests/regression/test_rc003_source_identity_semantics.py"
            ],
            "application_snapshot": "a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-002/7de07b54-693f-4d45-a422-e42ea3cd543a/environment.json",
            "stdout": "runs/rc-002/7de07b54-693f-4d45-a422-e42ea3cd543a/stdout.txt",
            "stderr": "runs/rc-002/7de07b54-693f-4d45-a422-e42ea3cd543a/stderr.txt",
            "structured_results": {
              "tests": 3,
              "failures": 2,
              "errors": 0,
              "skipped": 0,
              "time": "0.032",
              "cases": [
                {
                  "classname": "tests.regression.test_rc003_source_identity_semantics",
                  "name": "test_exact_replay_does_not_create_duplicate",
                  "status": "failed",
                  "time": "0.002"
                },
                {
                  "classname": "tests.regression.test_rc003_source_identity_semantics",
                  "name": "test_source_identity_conflict_raises_and_preserves_original",
                  "status": "failed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.regression.test_rc003_source_identity_semantics",
                  "name": "test_distinct_source_record_ids_with_identical_business_fields_both_stored",
                  "status": "passed",
                  "time": "0.002"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-002/7de07b54-693f-4d45-a422-e42ea3cd543a/execution.json",
          "junit": "evidence/runs/rc-002/7de07b54-693f-4d45-a422-e42ea3cd543a/junit.xml",
          "stdout": "evidence/runs/rc-002/7de07b54-693f-4d45-a422-e42ea3cd543a/stdout.txt"
        },
        "verification": {
          "record": {
            "execution_id": "8fc097e1-07f1-46ec-b558-8cdf84e7a95f",
            "phase": "verification",
            "started_at": "2026-09-26T10:09:30.382288+00:00",
            "duration_ms": 358,
            "exit_code": 0,
            "outcome": "passed",
            "pytest_targets": [
              "tests/regression/test_rc003_source_identity_semantics.py"
            ],
            "application_snapshot": "a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-002/8fc097e1-07f1-46ec-b558-8cdf84e7a95f/environment.json",
            "stdout": "runs/rc-002/8fc097e1-07f1-46ec-b558-8cdf84e7a95f/stdout.txt",
            "stderr": "runs/rc-002/8fc097e1-07f1-46ec-b558-8cdf84e7a95f/stderr.txt",
            "structured_results": {
              "tests": 3,
              "failures": 0,
              "errors": 0,
              "skipped": 0,
              "time": "0.014",
              "cases": [
                {
                  "classname": "tests.regression.test_rc003_source_identity_semantics",
                  "name": "test_exact_replay_does_not_create_duplicate",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.regression.test_rc003_source_identity_semantics",
                  "name": "test_source_identity_conflict_raises_and_preserves_original",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.regression.test_rc003_source_identity_semantics",
                  "name": "test_distinct_source_record_ids_with_identical_business_fields_both_stored",
                  "status": "passed",
                  "time": "0.001"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-002/8fc097e1-07f1-46ec-b558-8cdf84e7a95f/execution.json",
          "junit": "evidence/runs/rc-002/8fc097e1-07f1-46ec-b558-8cdf84e7a95f/junit.xml",
          "stdout": "evidence/runs/rc-002/8fc097e1-07f1-46ec-b558-8cdf84e7a95f/stdout.txt"
        },
        "baseline": {
          "record": {
            "execution_id": "81715fe2-3ecd-4047-90ff-fba8c105b325",
            "phase": "verification",
            "started_at": "2026-09-26T10:09:39.915986+00:00",
            "duration_ms": 297,
            "exit_code": 0,
            "outcome": "passed",
            "pytest_targets": [
              "tests/existing"
            ],
            "application_snapshot": "a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395",
            "protected_manifest": {
              "ok": true,
              "missing": [],
              "modified": []
            },
            "environment_manifest": "runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/environment.json",
            "stdout": "runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/stdout.txt",
            "stderr": "runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/stderr.txt",
            "structured_results": {
              "tests": 5,
              "failures": 0,
              "errors": 0,
              "skipped": 0,
              "time": "0.016",
              "cases": [
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_single_line_item_import",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_stored_contents_retrievable",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_multiple_line_items_same_invoice",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_stored_invoice_identifiers_match_expected",
                  "status": "passed",
                  "time": "0.001"
                },
                {
                  "classname": "tests.existing.test_happy_path",
                  "name": "test_lookup_returns_only_matching_invoice",
                  "status": "passed",
                  "time": "0.001"
                }
              ]
            }
          },
          "json": "evidence/runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/execution.json",
          "junit": "evidence/runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/junit.xml",
          "stdout": "evidence/runs/rc-002/81715fe2-3ecd-4047-90ff-fba8c105b325/stdout.txt"
        }
      }
    }
  ]
};
