"""
Retail transaction line-item importer.

Accepts raw input records, applies normalization, and persists them via the
database module.
"""

import sqlite3
from typing import Any, Dict, List

from sample_app import database


def _normalize(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return a normalized copy of *record* ready for storage."""
    normalized_invoice = str(int(record["invoice_no"]))
    return {
        "source_record_id": str(record["source_record_id"]),
        "invoice_no": normalized_invoice,
        "stock_code": str(record["stock_code"]),
        "quantity": int(record["quantity"]),
        "unit_price": float(record["unit_price"]),
    }


def import_record(conn: sqlite3.Connection, record: Dict[str, Any]) -> int:
    """Normalize and persist a single line-item record.

    Returns the generated row id.
    """
    normalized = _normalize(record)
    return database.insert_line_item(conn, normalized)


def import_records(
    conn: sqlite3.Connection, records: List[Dict[str, Any]]
) -> List[int]:
    """Normalize and persist a list of line-item records.

    Returns the list of generated row ids in the same order as *records*.
    """
    return [import_record(conn, r) for r in records]
