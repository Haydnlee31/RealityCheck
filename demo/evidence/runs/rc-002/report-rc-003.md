# RealityCheck Evidence Report
**Run:** `rc-002`  
**Finding:** `RC-003`  
**Schema version:** `1.0`  

---
## Legend
This report distinguishes two kinds of content:

- **Model interpretation** — requirement analysis, implementation assumption, counterexample, and proposed relationship between code and contract. These are model-authored and were reviewed by a developer before acceptance.
- **Deterministic observation** — execution IDs, exit codes, pass/fail/error/timeout, protected-manifest hashes, and application snapshot IDs. These are recorded by the deterministic `realitycheck.runner` tooling; no LLM judgment is applied.


---
## Requirement _(model interpretation)_
> **Model interpretation** — requirement identified and classified by the model. Sources are cited verbatim from the referenced documents.

**ID:** AC-004 / AC-005 / AC-006  
**Classification:** documented  

AC-004: Re-importing the same source_record_id with identical record contents must not create another stored row. AC-005: If an already-seen source_record_id is supplied again with different record contents, the application must fail clearly (ValueError mentioning 'source_record_id'); the original stored row must remain unchanged. AC-006: Two records with different source_record_id values must both be preserved even if all business fields are otherwise identical.

### Sources
- **application-contract** — `docs/application-contract.md` @ `Lines 64–100, sections 'AC-004 — Exact replay safety', 'AC-005 — Source identity conflict', 'AC-006 — Equal business values do not imply duplicate identity'`  


---
## Implementation Assumption _(model interpretation)_
> **Model interpretation** — how the model assessed the implementation as diverging from the requirement. Reviewed and accepted by the developer before any repair.

import_record() called insert_line_item() unconditionally. No prior SELECT was performed. No UNIQUE constraint existed on source_record_id. Identical replays created duplicate rows (AC-004 violated). Conflicting re-imports were silently accepted as a second row (AC-005 violated). AC-006 was already compliant by virtue of the schema having no UNIQUE constraint on business fields.

**Code artifact:** `sample_app/importer.py`  
**Symbol:** `import_record`  

---
## Counterexample _(model interpretation)_
> **Model interpretation** — minimal input the model identified as exercising the mismatch. Developer-accepted before the regression test was written.

**Kind:** input-record  
**Fixture:** _not recorded_  
**Record IDs:** sid-replay-001, sid-conflict-001, dup-sid-001, dup-sid-002  

**Expected behavior:**  
AC-004: two identical imports of sid-replay-001 must produce exactly 1 stored row. AC-005: re-import of sid-conflict-001 with changed fields must raise ValueError mentioning 'source_record_id'; original row must be unchanged. AC-006: dup-sid-001 and dup-sid-002 with identical business fields must both be independently stored.


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

**Test artifact:** tests/regression/test_rc003_source_identity_semantics.py  
**Node IDs:** `tests/regression/test_rc003_source_identity_semantics.py::test_exact_replay_does_not_create_duplicate`, `tests/regression/test_rc003_source_identity_semantics.py::test_source_identity_conflict_raises_and_preserves_original`, `tests/regression/test_rc003_source_identity_semantics.py::test_distinct_source_record_ids_with_identical_business_fields_both_stored`  
**Expected failure (on unrepaired app):** test_exact_replay_does_not_create_duplicate: AssertionError: AC-004 violated — 2 row(s) stored for source_record_id 'sid-replay-001'; expected exactly 1. test_source_identity_conflict_raises_and_preserves_original: Failed: DID NOT RAISE <class 'ValueError'>. test_distinct_source_record_ids_…: passes on unmodified application (regression guard).  

---
## Protected-Manifest Verification _(deterministic observations)_
> **Deterministic observation** — hash verification performed by the runner at each execution phase. A FAILED status immediately blocks the verdict.

| Phase | Execution ID | Status | Changed/Missing |
|-------|-------------|--------|------------------|
| Reproduction | `7de07b54-693f-4d45-a422-e42ea3cd543a` | ✓ verified | — |
| Verification (regression) | `8fc097e1-07f1-46ec-b558-8cdf84e7a95f` | ✓ verified | — |
| Verification (baseline) | `81715fe2-3ecd-4047-90ff-fba8c105b325` | ✓ verified | — |


---
## Execution Results _(deterministic observations)_
> **Deterministic observation** — all execution outcomes below are recorded by the runner. No LLM judgment is applied to determine pass or fail.

### Reproduction Execution

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `7de07b54-693f-4d45-a422-e42ea3cd543a`  

**Phase:** reproduction  

**Started at:** 2026-09-26T10:05:37.859236+00:00  

**Duration (ms):** 394  

**Exit code:** 1  

**Outcome:** **failed**  

**Pytest targets:** `tests/regression/test_rc003_source_identity_semantics.py`  

**Application snapshot:** `a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=3  failures=2  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✗ failed | `tests.regression.test_rc003_source_identity_semantics.test_exact_replay_does_not_create_duplicate` | 0.002 |

| ✗ failed | `tests.regression.test_rc003_source_identity_semantics.test_source_identity_conflict_raises_and_preserves_original` | 0.001 |

| ✓ passed | `tests.regression.test_rc003_source_identity_semantics.test_distinct_source_record_ids_with_identical_business_fields_both_stored` | 0.002 |



### Verification Execution — Regression Test

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `8fc097e1-07f1-46ec-b558-8cdf84e7a95f`  

**Phase:** verification  

**Started at:** 2026-09-26T10:09:30.382288+00:00  

**Duration (ms):** 358  

**Exit code:** 0  

**Outcome:** **passed**  

**Pytest targets:** `tests/regression/test_rc003_source_identity_semantics.py`  

**Application snapshot:** `a2beaf7c291ec84f012f65c37006432909e1fc2b87d3e1d59957bfd62f33b395`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=3  failures=0  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✓ passed | `tests.regression.test_rc003_source_identity_semantics.test_exact_replay_does_not_create_duplicate` | 0.001 |

| ✓ passed | `tests.regression.test_rc003_source_identity_semantics.test_source_identity_conflict_raises_and_preserves_original` | 0.001 |

| ✓ passed | `tests.regression.test_rc003_source_identity_semantics.test_distinct_source_record_ids_with_identical_business_fields_both_stored` | 0.001 |



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
--- a/sample_app/database.py
+++ b/sample_app/database.py
+ def get_line_item_by_source_id(conn, source_record_id) -> Optional[dict]:
+     ...
--- a/sample_app/importer.py
+++ b/sample_app/importer.py
+ def _check_source_identity(conn, normalized):
+     # AC-004: identical replay -> raise _ExactReplay
+     # AC-005: conflicting re-import -> raise ValueError
+ class _ExactReplay(Exception): ...
+ import_record: pre-INSERT _check_source_identity call added
+ import_records: transaction envelope added (see RC-002 patch)
```

---
## Verdict _(deterministic observation)_
> **Deterministic observation** — verdict derived from execution records by `realitycheck.runner.compute_verdict`. Not a model-generated assessment.

**Status:** **verified_for_tested_scenarios**  
**Reason:** Verification execution passed all required tests  

**Limitations:**

- Verdict covers only the tested scenarios — not all contract requirements.
- AC-006 was already compliant on the unmodified application; its test is a regression guard only.
- The AC-005 exception type (ValueError) is a developer-accepted interface decision recorded in acceptance.ac005_exception_type_decision.

