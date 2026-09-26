"""
Regression test for RC-001.

Requirement: AC-001 — Invoice identifier preservation
Source: docs/application-contract.md, lines 10–24

AC-001 requires that invoice_no is treated as an opaque string and preserved
byte-for-byte through ingestion, storage, and retrieval.  The application must
not apply integer coercion or any other transformation that removes leading
zeros.

Counterexample provenance: "053636" is a **synthetic, contract-derived**
counterexample.  It was hand-authored to exercise the leading-zero edge case
implied by AC-001.  It is not extracted from or representative of any record
in the UCI Online Retail dataset (see docs/source-notes.md).
"""

import os
import tempfile

import pytest

from sample_app import database, importer


@pytest.fixture
def db_conn():
    """Yield an initialised connection backed by a temp file, cleaned up after the test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
    conn = database.connect(db_path)
    database.init_schema(conn)
    yield conn
    conn.close()
    os.unlink(db_path)


def test_leading_zero_invoice_no_preserved(db_conn):
    """
    AC-001: invoice_no with a leading zero must survive ingestion unchanged.

    Counterexample: invoice_no="053636" — str(int("053636")) produces "53636",
    which is a byte-for-byte different identifier.  The stored value must equal
    "053636" and a lookup by "053636" must return exactly this record.

    Expected failure on unmodified application: _normalize() in importer.py
    applies str(int(...)) which strips the leading zero, so the lookup by
    "053636" returns zero rows and the len assertion fails.
    """
    record = {
        "source_record_id": "rc-001",
        "invoice_no": "053636",
        "stock_code": "ABC",
        "quantity": 1,
        "unit_price": 1.00,
    }

    importer.import_record(db_conn, record)

    # Lookup must succeed with the original identifier
    results = database.get_line_items_by_invoice(db_conn, "053636")
    assert len(results) == 1, (
        "Lookup by original invoice_no='053636' returned no rows — "
        "identifier was likely mutated during import"
    )

    # Stored value must equal the original byte-for-byte
    assert results[0]["invoice_no"] == "053636", (
        f"Stored invoice_no {results[0]['invoice_no']!r} != '053636' — "
        "integer coercion stripped the leading zero"
    )
