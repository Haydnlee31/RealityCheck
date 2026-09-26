"""
Contract-violation test for AC-001 — Invoice identifier preservation.

AC-001 states:
  - invoice_no is an opaque string identifier.
  - The application must preserve the received identifier unchanged through
    ingestion, storage, and retrieval.
  - Transformations such as integer coercion, padding removal, or case folding
    are prohibited.

The bug: importer._normalize() applies str(int(record["invoice_no"])), which
strips leading zeros (e.g. "0536365" → "536365"), violating AC-001.
"""

import os
import tempfile

import pytest

from sample_app import database, importer


@pytest.fixture
def db_conn():
    """Yield an initialised connection backed by a temp file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
    conn = database.connect(db_path)
    database.init_schema(conn)
    yield conn
    conn.close()
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# AC-001 — leading-zero invoice_no must be stored and retrieved unchanged
# ---------------------------------------------------------------------------

def test_leading_zero_invoice_no_preserved(db_conn):
    """
    An invoice_no that starts with a leading zero must survive the import
    pipeline byte-for-byte.

    Before the fix, str(int("0536365")) == "536365", so the stored value
    would differ from the input and a lookup by the original identifier would
    return no rows.
    """
    record = {
        "source_record_id": "ac001-001",
        "invoice_no": "0536365",   # leading zero — opaque string identifier
        "stock_code": "85123A",
        "quantity": 6,
        "unit_price": 2.55,
    }

    importer.import_record(db_conn, record)

    # The lookup must use the exact identifier supplied at import time.
    results = database.get_line_items_by_invoice(db_conn, "0536365")

    assert len(results) == 1, (
        "Expected 1 row for invoice_no='0536365', "
        f"got {len(results)}. "
        "The importer is likely stripping leading zeros via int() coercion."
    )
    assert results[0]["invoice_no"] == "0536365", (
        f"Stored invoice_no {results[0]['invoice_no']!r} != original '0536365'. "
        "Integer coercion has altered the identifier."
    )
