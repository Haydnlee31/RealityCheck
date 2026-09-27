"""
Regression test for RC-002 / AC-007 — Batch atomicity.

Requirement source: docs/application-contract.md, lines 104–113,
section "AC-007 — Batch atomicity".

AC-007 requires that import_records() is atomic: if any record in a batch
fails, no records newly inserted by that batch may remain persisted.  The
database must be identical to its pre-batch state after a failure.

Failure trigger used here: the third record is missing the required
'unit_price' field, which causes _normalize() to raise KeyError: 'unit_price'.

Expected failure on the unmodified application:
    AssertionError: AC-007 violated — 2 record(s) from the failed batch
    remain persisted: ['batch-new-001', 'batch-new-002']

The failure occurs because insert_line_item() commits each row individually
and import_records() has no surrounding transaction or rollback.
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


def test_failed_batch_leaves_no_partial_rows(db_conn):
    """AC-007: a batch that raises mid-way must not leave partial rows.

    Setup: one pre-existing record is imported before the batch so we can
    confirm it survives unchanged (the contract says only *newly inserted*
    rows from the failing batch must be absent).

    The batch contains two valid records followed by one record that is
    missing the required 'unit_price' field.  _normalize() raises
    KeyError: 'unit_price' on the third record.

    After the exception the database must contain only the pre-existing row.
    """
    # Establish a pre-existing row that must survive unchanged.
    importer.import_record(db_conn, {
        "source_record_id": "batch-exist-001",
        "invoice_no":       "INV-EXIST",
        "stock_code":       "SKU-E",
        "quantity":         1,
        "unit_price":       1.00,
    })

    batch = [
        {
            "source_record_id": "batch-new-001",
            "invoice_no":       "INV-BATCH",
            "stock_code":       "SKU-A",
            "quantity":         5,
            "unit_price":       9.99,
        },
        {
            "source_record_id": "batch-new-002",
            "invoice_no":       "INV-BATCH",
            "stock_code":       "SKU-B",
            "quantity":         3,
            "unit_price":       4.50,
        },
        {
            # Missing 'unit_price' — _normalize() raises KeyError: 'unit_price'
            "source_record_id": "batch-bad-003",
            "invoice_no":       "INV-BATCH",
            "stock_code":       "SKU-C",
            "quantity":         1,
        },
    ]

    with pytest.raises(KeyError, match="unit_price"):
        importer.import_records(db_conn, batch)

    # AC-007: no newly inserted rows from the failed batch may remain.
    batch_rows = database.get_line_items_by_invoice(db_conn, "INV-BATCH")
    assert len(batch_rows) == 0, (
        f"AC-007 violated — {len(batch_rows)} record(s) from the failed batch "
        f"remain persisted: {[r['source_record_id'] for r in batch_rows]}"
    )

    # Pre-existing row must remain intact and unchanged.
    pre_rows = database.get_line_items_by_invoice(db_conn, "INV-EXIST")
    assert len(pre_rows) == 1
    assert pre_rows[0]["source_record_id"] == "batch-exist-001"
