"""
Baseline happy-path tests for the retail transaction line-item importer.

Each test uses a fresh temporary SQLite database so tests are fully isolated.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from sample_app import database, importer

FIXTURES_PATH = Path(__file__).parent.parent.parent / "fixtures" / "development.jsonl"


def _load_fixture() -> list:
    records = []
    with open(FIXTURES_PATH) as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


@pytest.fixture
def db_conn():
    """Yield an initialised in-memory-style connection backed by a temp file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
    conn = database.connect(db_path)
    database.init_schema(conn)
    yield conn
    conn.close()
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Test 1 — a single numeric-invoice line item can be imported
# ---------------------------------------------------------------------------

def test_single_line_item_import(db_conn):
    record = {
        "source_record_id": "dev-001",
        "invoice_no": "536365",
        "stock_code": "85123A",
        "quantity": 6,
        "unit_price": 2.55,
    }
    row_id = importer.import_record(db_conn, record)
    assert isinstance(row_id, int)
    assert row_id > 0


# ---------------------------------------------------------------------------
# Test 2 — stored contents can be retrieved
# ---------------------------------------------------------------------------

def test_stored_contents_retrievable(db_conn):
    record = {
        "source_record_id": "dev-004",
        "invoice_no": "536366",
        "stock_code": "22752",
        "quantity": 2,
        "unit_price": 1.85,
    }
    importer.import_record(db_conn, record)
    results = database.get_line_items_by_invoice(db_conn, "536366")

    assert len(results) == 1
    row = results[0]
    assert row["source_record_id"] == "dev-004"
    assert row["stock_code"] == "22752"
    assert row["quantity"] == 2
    assert abs(row["unit_price"] - 1.85) < 1e-9


# ---------------------------------------------------------------------------
# Test 3 — multiple line items sharing the same invoice number are returned
# ---------------------------------------------------------------------------

def test_multiple_line_items_same_invoice(db_conn):
    records = [r for r in _load_fixture() if r["invoice_no"] == "536365"]
    assert len(records) == 3, "fixture must contain exactly 3 records for invoice 536365"

    importer.import_records(db_conn, records)

    results = database.get_line_items_by_invoice(db_conn, "536365")
    assert len(results) == 3

    returned_ids = {r["source_record_id"] for r in results}
    assert returned_ids == {"dev-001", "dev-002", "dev-003"}


# ---------------------------------------------------------------------------
# Test 4 — stored invoice identifiers equal their expected values
# ---------------------------------------------------------------------------

def test_stored_invoice_identifiers_match_expected(db_conn):
    fixture = _load_fixture()
    importer.import_records(db_conn, fixture)

    for expected_invoice in ("536365", "536366", "536367"):
        results = database.get_line_items_by_invoice(db_conn, expected_invoice)
        assert len(results) >= 1, f"no rows found for invoice {expected_invoice}"
        for row in results:
            assert row["invoice_no"] == expected_invoice, (
                f"stored invoice_no {row['invoice_no']!r} "
                f"!= expected {expected_invoice!r}"
            )


# ---------------------------------------------------------------------------
# Test 5 — lookup for one invoice does not return rows from another
# ---------------------------------------------------------------------------

def test_lookup_returns_only_matching_invoice(db_conn):
    fixture = _load_fixture()
    importer.import_records(db_conn, fixture)

    results = database.get_line_items_by_invoice(db_conn, "536366")
    assert all(r["invoice_no"] == "536366" for r in results)
    assert all(r["source_record_id"] == "dev-004" for r in results)
