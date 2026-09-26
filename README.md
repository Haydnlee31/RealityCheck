# RealityCheck — Sample Application

A small Python + SQLite retail transaction ingestion application used as the
target system for the RealityCheck hackathon project.

---

## What the application does

The application imports retail transaction **line items** from structured input
records and stores them in a local SQLite database.  Each stored record
represents one source line item.  Line items can be retrieved by invoice
identifier; multiple line items may share the same invoice number.

---

## Install dependencies

Python 3.10 or later is required.

```bash
pip install -e ".[dev]"
```

---

## Run the baseline tests

```bash
pytest tests/existing/
```

---

## Data provenance

Later verification work will use the **UCI Online Retail** dataset as public
input provenance.  Fixtures currently present in `fixtures/` are synthetic
development fixtures; see `fixtures/manifest.json` for provenance details.
