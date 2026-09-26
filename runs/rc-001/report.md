# RealityCheck Evidence Report
**Run:** `rc-001`  
**Finding:** `RC-001`  
**Schema version:** `1.0`  

---
## Requirement
> _The following requirement was identified by investigation. Classification and sources are model-authored unless marked otherwise._

**ID:** AC-001  
**Classification:** documented  

invoice_no is an opaque string identifier at the application input boundary. The application must preserve the received identifier unchanged through ingestion, storage, and retrieval. The application must not infer numeric or any other type-specific semantics from the identifier string. Transformations such as integer coercion, padding removal, or case folding are prohibited. Observable requirement: After a record with invoice_no = X is imported, a lookup by invoice_no = X must return that record and the stored invoice_no field must equal X byte-for-byte.

### Sources
- **application-contract** — `docs/application-contract.md` @ `Lines 10–24, section 'AC-001 — Invoice identifier preservation'`  
  > The application must not infer numeric or any other type-specific semantics from the identifier string. Transformations such as integer coercion, padding removal, or case folding are prohibited.  
- **source-notes** — `docs/source-notes.md` @ `Lines 36–40, section 'Relationship to our application contract'`  
  > Our contract (AC-001) treats invoice_no as an opaque string. The application must not rely on publisher-specific identifier conventions.  


---
## Implementation Assumption
> _Model-authored interpretation of how the implementation diverges from the requirement._

The _normalize function assumes invoice_no is always a pure numeric string. It applies str(int(record["invoice_no"])) which coerces to integer then back to string. This silently strips leading zeros from identifiers such as "053636" (producing "53636") and raises ValueError for non-numeric identifiers.

**Code artifact:** `sample_app/importer.py`  
**Symbol:** `_normalize`  

---
## Counterexample
> _Model-authored counterexample demonstrating the divergence._

**Kind:** input-record  
**Fixture:** _not recorded_  
**Record IDs:** rc-001  

**Expected behavior:**  
After importing {"source_record_id": "rc-001", "invoice_no": "053636", ...}, a lookup by invoice_no="053636" must return exactly one record whose stored invoice_no field equals "053636" byte-for-byte. Counterexample provenance: synthetic, contract-derived. Not extracted from or representative of any record in the UCI Online Retail dataset (see docs/source-notes.md).


---
## Developer Acceptance
> _This section is completed by a human developer, not the model._

**Decision:** accepted  
**Reviewer:** developer (explicit ACCEPT reply)  
**Timestamp:** 2026-09-26T08:42:00+00:00  
**Protected manifest:** runs/rc-001/protected-manifest.json  

---
## Regression Test
> _Accepted regression test artifact — must not be modified after acceptance._

**Test artifact:** tests/regression/test_rc001_invoice_no_preservation.py  
**Node IDs:** `tests/regression/test_rc001_invoice_no_preservation.py::test_leading_zero_invoice_no_preserved`  
**Expected failure:** On the unmodified application, _normalize strips the leading zero from "053636" producing "53636" before storage. The lookup by "053636" returns zero rows, so the assertion len(results) == 1 fails with AssertionError: Lookup by original invoice_no='053636' returned no rows.  

---
## Execution Results
> _All execution outcomes below are deterministic records from the runner. No LLM judgment is applied._

### Reproduction Execution

**Phase:** reproduction  

**Outcome:** failed  

**Exit code:** _not recorded_  

**Duration (ms):** _not recorded_  

**Started at:** _not recorded_  

**Pytest targets:**   

**Application snapshot:** _not recorded_  

### Verification Execution

**Phase:** verification  

**Outcome:** passed  

**Exit code:** _not recorded_  

**Duration (ms):** _not recorded_  

**Started at:** _not recorded_  

**Pytest targets:**   

**Application snapshot:** _not recorded_  

---
## Repair
**Base snapshot:** 3e7416b56e789479b88372315cba35b816da91b4906dd64c2509b04a0e8ef87b  
**Candidate snapshot:** a0efceb71f4b664c039a14166eecf71d80825798c526a758c7a65ca8c5f7a4c1  

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
## Verdict
> _Deterministic verdict derived from execution records. Not a model-generated assessment._

**Status:** **verified_for_tested_scenarios**  
**Reason:** Verification execution passed all required tests  

**Limitations:**

- Verdict covers only the tested scenarios — not all contract requirements.
- The counterexample input (invoice_no="053636") is synthetic and contract-derived. It is not extracted from the UCI Online Retail dataset.
- AC-002 and AC-003 are not independently regression-tested in this run.

