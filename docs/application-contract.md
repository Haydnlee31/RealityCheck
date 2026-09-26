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
