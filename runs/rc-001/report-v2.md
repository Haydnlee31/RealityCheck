# RealityCheck Evidence Report
**Run:** `rc-001`  
**Finding:** `RC-001`  
**Schema version:** `1.0`  

---
## Legend
This report distinguishes two kinds of content:

- **Model interpretation** — requirement analysis, implementation assumption, counterexample, and proposed relationship between code and contract. These are model-authored and were reviewed by a developer before acceptance.
- **Deterministic observation** — execution IDs, exit codes, pass/fail/error/timeout, protected-manifest hashes, and application snapshot IDs. These are recorded by the deterministic `realitycheck.runner` tooling; no LLM judgment is applied.


---
## Requirement _(model interpretation)_
> **Model interpretation** — requirement identified and classified by the model. Sources are cited verbatim from the referenced documents.

**ID:** AC-001  
**Classification:** documented  

invoice_no is an opaque string identifier at the application input boundary. The application must preserve the received identifier unchanged through ingestion, storage, and retrieval. The application must not infer numeric or any other type-specific semantics from the identifier string. Transformations such as integer coercion, padding removal, or case folding are prohibited. Observable requirement: After a record with invoice_no = X is imported, a lookup by invoice_no = X must return that record and the stored invoice_no field must equal X byte-for-byte.

### Sources
- **application-contract** — `docs/application-contract.md` @ `Lines 10–24, section 'AC-001 — Invoice identifier preservation'`  
  > The application must not infer numeric or any other type-specific semantics from the identifier string. Transformations such as integer coercion, padding removal, or case folding are prohibited.  
- **source-notes** — `docs/source-notes.md` @ `Lines 36–40, section 'Relationship to our application contract'`  
  > Our contract (AC-001) treats invoice_no as an opaque string. The application must not rely on publisher-specific identifier conventions.  


---
## Implementation Assumption _(model interpretation)_
> **Model interpretation** — how the model assessed the implementation as diverging from the requirement. Reviewed and accepted by the developer before any repair.

The _normalize function assumes invoice_no is always a pure numeric string. It applies str(int(record["invoice_no"])) which coerces to integer then back to string. This silently strips leading zeros from identifiers such as "053636" (producing "53636") and raises ValueError for non-numeric identifiers.

**Code artifact:** `sample_app/importer.py`  
**Symbol:** `_normalize`  

---
## Counterexample _(model interpretation)_
> **Model interpretation** — minimal input the model identified as exercising the mismatch. Developer-accepted before the regression test was written.

**Kind:** input-record  
**Fixture:** _not recorded_  
**Record IDs:** rc-001  

**Expected behavior:**  
After importing {"source_record_id": "rc-001", "invoice_no": "053636", ...}, a lookup by invoice_no="053636" must return exactly one record whose stored invoice_no field equals "053636" byte-for-byte. Counterexample provenance: synthetic, contract-derived. Not extracted from or representative of any record in the UCI Online Retail dataset (see docs/source-notes.md).


---
## Developer Acceptance
> _This section records an explicit human decision. The workflow does not proceed past this point without ACCEPT._

**Decision:** accepted  
**Reviewer:** developer (explicit ACCEPT reply)  
**Timestamp:** 2026-09-26T08:42:00+00:00  
**Protected manifest:** runs/rc-001/protected-manifest.json  

---
## Regression Test
> _Accepted regression test artifact — must not be modified after acceptance._

**Test artifact:** tests/regression/test_rc001_invoice_no_preservation.py  
**Node IDs:** `tests/regression/test_rc001_invoice_no_preservation.py::test_leading_zero_invoice_no_preserved`  
**Expected failure (on unrepaired app):** On the unmodified application, _normalize strips the leading zero from "053636" producing "53636" before storage. The lookup by "053636" returns zero rows, so the assertion len(results) == 1 fails with AssertionError: Lookup by original invoice_no='053636' returned no rows.  

---
## Protected-Manifest Verification _(deterministic observations)_
> **Deterministic observation** — hash verification performed by the runner at each execution phase. A FAILED status immediately blocks the verdict.

| Phase | Execution ID | Status | Changed/Missing |
|-------|-------------|--------|------------------|
| Reproduction | `df96ba74-10dd-4505-87e7-b7136736d835` | ✓ verified | — |
| Verification (regression) | `5fb09aa4-2f09-4ff5-83ef-ca717c023f6b` | ✓ verified | — |
| Verification (baseline) | `fae0e1d9-b45a-475c-8dbc-e384fcdd32e6` | ✓ verified | — |


---
## Execution Results _(deterministic observations)_
> **Deterministic observation** — all execution outcomes below are recorded by the runner. No LLM judgment is applied to determine pass or fail.

### Reproduction Execution

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `df96ba74-10dd-4505-87e7-b7136736d835`  

**Phase:** reproduction  

**Started at:** 2026-09-26T08:42:48.127541+00:00  

**Duration (ms):** 547  

**Exit code:** 1  

**Outcome:** **failed**  

**Pytest targets:** `tests/regression/test_rc001_invoice_no_preservation.py::test_leading_zero_invoice_no_preserved`  

**Application snapshot:** `3e7416b56e789479b88372315cba35b816da91b4906dd64c2509b04a0e8ef87b`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=1  failures=1  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✗ failed | `tests.regression.test_rc001_invoice_no_preservation.test_leading_zero_invoice_no_preserved` | 0.002 |



### Verification Execution — Regression Test

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `5fb09aa4-2f09-4ff5-83ef-ca717c023f6b`  

**Phase:** verification  

**Started at:** 2026-09-26T08:46:09.820822+00:00  

**Duration (ms):** 437  

**Exit code:** 0  

**Outcome:** **passed**  

**Pytest targets:** `tests/regression/test_rc001_invoice_no_preservation.py::test_leading_zero_invoice_no_preserved`  

**Application snapshot:** `a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=1  failures=0  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✓ passed | `tests.regression.test_rc001_invoice_no_preservation.test_leading_zero_invoice_no_preserved` | 0.002 |



### Verification Execution — Baseline Preservation

> _Deterministic observation — values recorded by the runner, not inferred by the model._


**Execution ID:** `fae0e1d9-b45a-475c-8dbc-e384fcdd32e6`  

**Phase:** verification  

**Started at:** 2026-09-26T08:46:10.259731+00:00  

**Duration (ms):** 286  

**Exit code:** 0  

**Outcome:** **passed**  

**Pytest targets:** `tests/existing`  

**Application snapshot:** `a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1`  

**Protected-manifest verification:** ✓ verified — all protected files present and unmodified  

**Test counts:** tests=5  failures=0  errors=0  skipped=0  


**Individual test results:**


| Status | Test | Time (s) |
|--------|------|----------|

| ✓ passed | `tests.existing.test_happy_path.test_single_line_item_import` | 0.001 |

| ✓ passed | `tests.existing.test_happy_path.test_stored_contents_retrievable` | 0.001 |

| ✓ passed | `tests.existing.test_happy_path.test_multiple_line_items_same_invoice` | 0.001 |

| ✓ passed | `tests.existing.test_happy_path.test_stored_invoice_identifiers_match_expected` | 0.002 |

| ✓ passed | `tests.existing.test_happy_path.test_lookup_returns_only_matching_invoice` | 0.003 |



---
## Repair
> **Deterministic observation** — snapshots are SHA-256 digests of the application directory tree computed by the runner.

**Base snapshot (pre-repair):** `3e7416b56e789479b88372315cba35b816da91b4906dd64c2509b04a0e8ef87b`  
**Candidate snapshot (post-repair):** `a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1`  

**Patch:**

```diff
diff --git a/sample_app/importer.py b/sample_app/importer.py
index c429e27..3bc10ae 100644
--- a/sample_app/importer.py
+++ b/sample_app/importer.py
@@ -13,7 +13,7 @@ from sample_app import database
 
 def _normalize(record: Dict[str, Any]) -> Dict[str, Any]:
     """Return a normalized copy of *record* ready for storage."""
-    normalized_invoice = str(int(record["invoice_no"]))
+    normalized_invoice = str(record["invoice_no"])
     return {
         "source_record_id": str(record["source_record_id"]),
         "invoice_no": normalized_invoice,

```

---
## Verdict _(deterministic observation)_
> **Deterministic observation** — verdict derived from execution records by `realitycheck.runner.compute_verdict`. Not a model-generated assessment.

**Status:** **verified_for_tested_scenarios**  
**Reason:** Verification execution passed all required tests  

**Limitations:**

- Verdict covers only the tested scenarios — not all contract requirements.
- The counterexample input (invoice_no="053636") is synthetic and contract-derived. It is not extracted from the UCI Online Retail dataset.
- AC-002 and AC-003 are not independently regression-tested in this run.

