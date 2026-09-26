"""
Regression tests for RC-003 / AC-004, RC-004 / AC-005, RC-005 / AC-006 —
Source-identity idempotence and conflict semantics.

Requirement sources: docs/application-contract.md, lines 64–100,
sections "AC-004 — Exact replay safety", "AC-005 — Source identity conflict",
and "AC-006 — Equal business values do not imply duplicate identity".

--- AC-005 exception-type decision (developer-accepted at acceptance checkpoint) ---
The contract (AC-005) states the application "must fail clearly" but does not
prescribe the exception type.  At the human acceptance checkpoint the developer
accepted the following interface decision:
    ValueError must be raised for a conflicting reuse of source_record_id,
    and the exception message must mention 'source_record_id'.
This decision is frozen here and must not be changed without a new acceptance
checkpoint.

--- Expected failures on the unmodified application ---
test_exact_replay_does_not_create_duplicate:
    AssertionError: AC-004 violated — 2 row(s) stored for
    source_record_id 'sid-replay-001'; expected exactly 1.
    (insert_line_item() is unconditional; no deduplication exists.)

test_source_identity_conflict_raises_and_preserves_original:
    Failed: DID NOT RAISE <class 'ValueError'>
    (import_record() performs no prior SELECT; the conflicting record is
    silently inserted as a second row.)

test_distinct_source_record_ids_with_identical_business_fields_both_stored:
    Expected to PASS on the unmodified application and after repair.
    (No UNIQUE constraint on business fields exists; this is a regression
    guard to prevent any future repair from introducing one.)
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


# ---------------------------------------------------------------------------
# AC-004 — Exact replay safety
# ---------------------------------------------------------------------------

def test_exact_replay_does_not_create_duplicate(db_conn):
    """AC-004: importing the same record twice must leave exactly one stored row.

    Both calls use byte-for-byte identical payloads.  The second call must be
    a no-op — it must not insert a second row.

    Observable check: retrieve all stored line items for the invoice and
    confirm exactly one row exists with the correct source_record_id.

    Expected failure on unmodified application:
        AssertionError: AC-004 violated — 2 row(s) stored for
        source_record_id 'sid-replay-001'; expected exactly 1.
    """
    record = {
        "source_record_id": "sid-replay-001",
        "invoice_no":       "INV-REPLAY",
        "stock_code":       "SKU-R",
        "quantity":         4,
        "unit_price":       2.50,
    }

    importer.import_record(db_conn, record)
    importer.import_record(db_conn, record)  # identical replay

    # Use the public lookup interface to observe the stored state.
    rows = database.get_line_items_by_invoice(db_conn, "INV-REPLAY")

    assert len(rows) == 1, (
        f"AC-004 violated — {len(rows)} row(s) stored for "
        f"source_record_id 'sid-replay-001'; expected exactly 1."
    )
    row = rows[0]
    assert row["source_record_id"] == "sid-replay-001"
    assert row["invoice_no"]       == "INV-REPLAY"
    assert row["stock_code"]       == "SKU-R"
    assert row["quantity"]         == 4
    assert abs(row["unit_price"] - 2.50) < 1e-9


# ---------------------------------------------------------------------------
# AC-005 — Source identity conflict
# ---------------------------------------------------------------------------

def test_source_identity_conflict_raises_and_preserves_original(db_conn):
    """AC-005: a re-import with the same source_record_id but different content
    must raise ValueError (mentioning 'source_record_id') and leave the original
    row unchanged.

    Exception-type decision: accepted at the human acceptance checkpoint —
    ValueError, message must mention 'source_record_id'.

    Observable checks:
      1. import_record() raises ValueError whose message includes 'source_record_id'.
      2. Exactly one row remains stored (no silent second insert).
      3. The stored row retains the original field values byte-for-byte.

    Expected failure on unmodified application:
        Failed: DID NOT RAISE <class 'ValueError'>
        (No conflict detection exists; the conflicting record is silently
        inserted, so the raises assertion fails immediately.)
    """
    original = {
        "source_record_id": "sid-conflict-001",
        "invoice_no":       "INV-C",
        "stock_code":       "SKU-ORIGINAL",
        "quantity":         5,
        "unit_price":       9.99,
    }
    conflicting = {
        "source_record_id": "sid-conflict-001",  # same id
        "invoice_no":       "INV-C",
        "stock_code":       "SKU-CHANGED",        # different
        "quantity":         99,                   # different
        "unit_price":       0.01,                 # different
    }

    importer.import_record(db_conn, original)

    # AC-005: must raise ValueError mentioning source_record_id.
    with pytest.raises(ValueError, match="source_record_id"):
        importer.import_record(db_conn, conflicting)

    # Original row must remain — use public lookup to observe stored state.
    rows = database.get_line_items_by_invoice(db_conn, "INV-C")

    assert len(rows) == 1, (
        f"AC-005 violated — {len(rows)} row(s) found for invoice 'INV-C'; "
        f"expected exactly 1 (the original)."
    )
    row = rows[0]
    assert row["source_record_id"] == "sid-conflict-001"
    assert row["stock_code"]       == "SKU-ORIGINAL", (
        f"AC-005 violated — original row was mutated; "
        f"stock_code is now {row['stock_code']!r}."
    )
    assert row["quantity"]   == 5
    assert abs(row["unit_price"] - 9.99) < 1e-9


# ---------------------------------------------------------------------------
# AC-006 — Equal business values do not imply duplicate identity
# ---------------------------------------------------------------------------

def test_distinct_source_record_ids_with_identical_business_fields_both_stored(db_conn):
    """AC-006: two records that share all business fields but carry distinct
    source_record_id values must both be independently stored and retrievable.

    This test is a regression guard: the current application already complies
    with AC-006.  Its purpose is to prevent any repair for AC-004 or AC-005
    from inadvertently introducing a UNIQUE constraint on business fields that
    would violate AC-006.

    Expected: passes on the unmodified application and must continue to pass
    after repair.
    """
    shared_fields = {
        "invoice_no": "INV-DUP",
        "stock_code": "SKU-DUP",
        "quantity":   5,
        "unit_price": 1.00,
    }

    importer.import_record(db_conn, {"source_record_id": "dup-sid-001", **shared_fields})
    importer.import_record(db_conn, {"source_record_id": "dup-sid-002", **shared_fields})

    rows = database.get_line_items_by_invoice(db_conn, "INV-DUP")

    assert len(rows) == 2, (
        f"AC-006 violated — only {len(rows)} row(s) stored; expected 2. "
        f"A deduplication strategy based on business fields has incorrectly "
        f"suppressed the second record."
    )
    sids = {r["source_record_id"] for r in rows}
    assert sids == {"dup-sid-001", "dup-sid-002"}
