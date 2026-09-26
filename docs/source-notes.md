# Source Notes — RealityCheck Sample Application

This document records provenance information for the data sources used in
development and verification of the sample application.

---

## Intended public dataset

The prototype uses the **UCI Online Retail** dataset as its primary input
provenance for later verification work.

- **Publisher:** UCI Machine Learning Repository
- **Dataset name:** Online Retail / Online Retail II
- **URL:** <https://archive.ics.uci.edu/dataset/352/online+retail>

---

## Publisher dataset conventions (as documented)

The following observations are drawn from publisher documentation and are
recorded here for reference. They have **not** been verified against a locally
downloaded copy of the workbook.

- Invoice identifiers are described as 6-digit numbers.
- Publisher documentation notes that invoices beginning with the letter **C**
  indicate cancellation transactions.
- No claim is made here about the exact form, frequency, or distribution of
  such identifiers without direct inspection of the source file.

---

## Relationship to our application contract

The publisher's description of invoice identifiers as 6-digit numeric codes
does **not** form part of the application contract defined in
`application-contract.md`.

Our contract (AC-001) treats `invoice_no` as an opaque string. The application
must not rely on publisher-specific identifier conventions.

---

## Synthetic fixtures

Fixtures in `fixtures/development.jsonl` are **synthetic** development
fixtures. They were hand-authored to exercise the application with
representative numeric invoice identifiers. They are **not** rows extracted
from the UCI dataset.

Fixture provenance is recorded in `fixtures/manifest.json`.

---

## Source workbook traceability

The following fields are to be completed once the source workbook has been
downloaded and inspected:

```
Source workbook SHA-256: <to be recorded>
Sheet:                   <to be recorded>
Exporter version:        <to be recorded>
Retrieval date:          <to be recorded>
```

Do not complete this section with fabricated values.
