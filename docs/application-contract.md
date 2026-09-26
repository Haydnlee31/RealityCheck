# Application Contract — RealityCheck Sample Application

**Scenario 1 — Retail Transaction Line-Item Ingestion**

This document is the authoritative contract for Scenario 1.
It describes required application behaviour at each observable boundary.

---

## AC-001 — Invoice identifier preservation

`invoice_no` is an **opaque string identifier** at the application input boundary.

The application **must** preserve the received identifier **unchanged** through
ingestion, storage, and retrieval.

The application **must not** infer numeric or any other type-specific semantics
from the identifier string. Transformations such as integer coercion, padding
removal, or case folding are prohibited.

**Observable requirement:** After a record with `invoice_no = X` is imported,
a lookup by `invoice_no = X` must return that record and the stored
`invoice_no` field must equal `X` byte-for-byte.

---

## AC-002 — Storage unit

One imported input record represents **one source line item**, not one complete
invoice.

Multiple source line items may share the same `invoice_no`.

**Observable requirement:** Importing N records that share the same
`invoice_no` must result in N independently retrievable stored line items.

---

## AC-003 — Invoice lookup

Looking up an `invoice_no` returns **all stored line items** associated with
that exact identifier.

The lookup must use exact string equality. Partial matching, numeric
equivalence, or any other relaxed comparison is prohibited.

**Observable requirement:** A lookup for identifier `X` returns every record
stored with `invoice_no = X`, and no records stored with a different identifier.

---

*End of contract for Scenario 1.*

---

**Scenario 2 — Source-Identity Idempotence and Batch Atomicity**

This section extends the contract with requirements governing how the application
must handle repeated or conflicting `source_record_id` values and multi-record
batch semantics.

---

## AC-004 — Exact replay safety

`source_record_id` identifies **one source line item** within the frozen import
source.

Re-importing the same `source_record_id` with **identical** record contents
**must not** create another stored row.

**Observable requirement:** After a record with `source_record_id = X` is
imported, importing that same record again (all fields byte-for-byte identical)
must leave exactly one stored row for `source_record_id = X`.

---

## AC-005 — Source identity conflict

If an already-seen `source_record_id` is supplied again with **different** record
contents, the application **must fail clearly**.

It **must not** silently ignore, overwrite, merge, or replace the existing record.

**Observable requirement:** Attempting to import a record whose `source_record_id`
matches a previously stored row but whose other fields differ must raise an error
that is visible to the caller. The original stored row must remain unchanged after
the attempt.

---

## AC-006 — Equal business values do not imply duplicate identity

Two records with **different** `source_record_id` values **must both be
preserved** even if all business fields (`invoice_no`, `stock_code`, `quantity`,
`unit_price`) are otherwise identical.

**Observable requirement:** Importing two records that share every business field
but carry distinct `source_record_id` values must result in two independently
retrievable stored rows.

---

## AC-007 — Batch atomicity

`import_records()` **must behave atomically**.

If any record in a batch fails validation or violates source-identity semantics,
no records **newly inserted** by that batch may remain persisted.

**Observable requirement:** After a batch import that fails partway through, the
set of stored rows must be identical to the set that existed before the batch
was invoked.

---

*End of contract for Scenario 2.*
