# RealityCheck Evidence Report
**Run:** `rc-002`  
**Finding:** `RC-002`  
**Schema version:** `1.0`  

---
## Legend
This report distinguishes two kinds of content:

- **Model interpretation** — requirement analysis, implementation assumption, counterexample, and proposed relationship between code and contract. These are model-authored and were reviewed by a developer before acceptance.
- **Deterministic observation** — execution IDs, exit codes, pass/fail/error/timeout, protected-manifest hashes, and application snapshot IDs. These are recorded by the deterministic `realitycheck.runner` tooling; no LLM judgment is applied.


---
## Requirement _(model interpretation)_
> **Model interpretation** — requirement identified and classified by the model. Sources are cited verbatim from the referenced documents.

**ID:** AC-007  
**Classification:** documented  

import_records() must behave atomically. If any record in a batch fails validation or violates source-identity semantics, no records newly inserted by that batch may remain persisted. Observable requirement: After a batch import that fails partway through, the set of stored rows must be identical to the set that existed before the batch was invoked.

### Sources
- **application-contract** — `docs/application-contract.md` @ `Lines 104–113, section 'AC-007 — Batch atomicity'`  
  > import_records() must behave atomically. If any record in a batch fails validation or violates source-identity semantics, no records newly inserted by that batch may remain persisted.  


---
## Implementation Assumption _(model interpretation)_
> **Model interpretation** — how the model assessed the implementation as diverging from the requirement. Reviewed and accepted by the developer before any repair.

import_records() was a bare list comprehension over import_record() calls. insert_line_item() committed after every individual INSERT. There was no BEGIN/ROLLBACK envelope. A failure on the N-th record left records 1..N-1 permanently committed.

**Code artifact:** `sample_app/importer.py`  
**Symbol:** `import_records`  

---
## Counterexample _(model interpretation)_
> **Model interpretation** — minimal input the model identified as exercising the mismatch. Developer-accepted before the regression test was written.

**Kind:** input-record  
**Fixture:** _not recorded_  
**Record IDs:** batch-new-001, batch-new-002, batch-bad-003  

**Expected behavior:**  
After import_records() raises KeyError('unit_price') on the third record, a lookup for invoice_no='INV-BATCH' must return 0 rows. The pre-existing row for 'INV-EXIST' must remain unchanged.


---
## Developer Acceptance
> _This section records an explicit human decision. The workflow does not proceed past this point without ACCEPT._

**Decision:** accepted  
**Reviewer:** developer (explicit ACCEPT reply)  
**Timestamp:** 2026-09-26T10:00:00+00:00  
**Protected manifest:** runs/rc-002/protected-manifest.json  

---
## Regression Test
> _Accepted regression test artifact — must not be modified after acceptance._

**Test artifact:** tests/regression/test_rc002_batch_atomicity.py  
**Node IDs:** `tests/regression/test_rc002_batch_atomicity.py::test_failed_batch_leaves_no_partial_rows`  
**Expected failure (on unrepaired app):** AssertionError: AC-007 violated — 2 record(s) from the failed batch remain persisted: ['batch-new-001', 'batch-new-002']  

---
## Protected-Manifest Verification _(deterministic observations)_
> **Deterministic observation** — hash verification performed by the runner at each execution phase. A FAILED status immediately blocks the verdict.

| Phase | Execution ID | Status | Changed/Missing |
|-------|-------------|--------|------------------|
| Reproduction | `07b5f2b6-5034-4d48-ae44-6b0f761a696e` | ✓ verified | — |
| Verification (regression) | `2bc00fd9-68ae-4246-ad39-4f94dfefd59f` | ✓ verified | — |
| Verification (baseline) | `81715fe2-3ecd-4047-90ff-fba8c105b325` | ✓ verified | — |


---
## Execution Results _(deterministic observations)_
> **Deterministic observation** — all execution outcomes below are recorded by the runner. No LLM judgment is applied to determine pass or fail.

### Reproduction Execution

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `07b5f2b6-5034-4d48-ae44-6b0f761a696e`  

**Phase:** reproduction  

**Started at:** 2026-09-26T10:05:10.192639+00:00  

**Duration (ms):** 470  

**Exit code:** 1  

**Outcome:** **failed**  

**Pytest targets:** `tests/regression/test_rc002_batch_atomicity.py::test_failed_batch_leaves_no_partial_rows`  

**Application snapshot:** `a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=1  failures=1  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✗ failed | `tests.regression.test_rc002_batch_atomicity.test_failed_batch_leaves_no_partial_rows` | 0.003 |



### Verification Execution — Regression Test

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `2bc00fd9-68ae-4246-ad39-4f94dfefd59f`  

**Phase:** verification  

**Started at:** 2026-09-26T10:09:02.214833+00:00  

**Duration (ms):** 430  

**Exit code:** 0  

**Outcome:** **passed**  

**Pytest targets:** `tests/regression/test_rc002_batch_atomicity.py::test_failed_batch_leaves_no_partial_rows`  

**Application snapshot:** `a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=1  failures=0  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✓ passed | `tests.regression.test_rc002_batch_atomicity.test_failed_batch_leaves_no_partial_rows` | 0.002 |



### Verification Execution — Baseline Preservation

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `81715fe2-3ecd-4047-90ff-fba8c105b325`  

**Phase:** verification  

**Started at:** 2026-09-26T10:09:39.915986+00:00  

**Duration (ms):** 297  

**Exit code:** 0  

**Outcome:** **passed**  

**Pytest targets:** `tests/existing`  

**Application snapshot:** `a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=5  failures=0  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✓ passed | `tests.existing.test_happy_path.test_single_line_item_import` | 0.001 |

| ✓ passed | `tests.existing.test_happy_path.test_stored_contents_retrievable` | 0.001 |

| ✓ passed | `tests.existing.test_happy_path.test_multiple_line_items_same_invoice` | 0.001 |

| ✓ passed | `tests.existing.test_happy_path.test_stored_invoice_identifiers_match_expected` | 0.001 |

| ✓ passed | `tests.existing.test_happy_path.test_lookup_returns_only_matching_invoice` | 0.001 |



---
## Repair
> **Deterministic observation** — snapshots are SHA-256 digests of the application directory tree computed by the runner.

**Base snapshot (pre-repair):** `a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1`  
**Candidate snapshot (post-repair):** `a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395`  

**Patch:**

```diff
--- a/sample_app/importer.py
+++ b/sample_app/importer.py
@@ import_records:
-    return [import_record(conn, r) for r in records]
+    conn.execute("BEGIN")
+    try:
+        for record in records: ...
+    except Exception:
+        conn.rollback()
+        raise
+    conn.commit()
+    return row_ids
--- a/sample_app/database.py
+++ b/sample_app/database.py
@@ insert_line_item:
-    conn.commit()
     return cursor.lastrowid
```

---
## Verdict _(deterministic observation)_
> **Deterministic observation** — verdict derived from execution records by `realitycheck.runner.compute_verdict`. Not a model-generated assessment.

**Status:** **verified_for_tested_scenarios**  
**Reason:** Verification execution passed all required tests  

**Limitations:**

- Verdict covers only the tested scenarios — not all contract requirements.
- The counterexample uses a missing-field KeyError as the batch-failure trigger. After AC-005 is implemented, a source-identity conflict is also a valid trigger.

