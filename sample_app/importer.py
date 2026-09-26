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
    normalized_invoice = str(record["invoice_no"])
    return {
        "source_record_id": str(record["source_record_id"]),
        "invoice_no": normalized_invoice,
        "stock_code": str(record["stock_code"]),
        "quantity": int(record["quantity"]),
        "unit_price": float(record["unit_price"]),
    }


def _check_source_identity(
    conn: sqlite3.Connection, normalized: Dict[str, Any]
) -> None:
    """Enforce AC-004 and AC-005 source-identity semantics.

    AC-004 — exact replay: if the stored row is byte-for-byte identical to
    *normalized*, this is a safe replay and the function returns normally.

    AC-005 — conflict: if a stored row exists but its fields differ, raise
    ValueError whose message mentions 'source_record_id'.

    If no stored row exists, the function returns normally.
    """
    existing = database.get_line_item_by_source_id(
        conn, normalized["source_record_id"]
    )
    if existing is None:
        return

    # Exact replay — all business fields must match byte-for-byte.
    if (
        existing["invoice_no"] == normalized["invoice_no"]
        and existing["stock_code"] == normalized["stock_code"]
        and existing["quantity"] == normalized["quantity"]
        and abs(existing["unit_price"] - normalized["unit_price"]) < 1e-9
    ):
        # AC-004: identical replay — treat as a no-op by signalling the caller.
        raise _ExactReplay

    # AC-005: same source_record_id, different content — must fail clearly.
    raise ValueError(
        f"source_record_id {normalized['source_record_id']!r} already exists "
        f"with different record contents; import rejected to protect source identity."
    )


class _ExactReplay(Exception):
    """Internal sentinel: the record is an exact replay of an existing row."""


def import_record(conn: sqlite3.Connection, record: Dict[str, Any]) -> int:
    """Normalize and persist a single line-item record.

    Returns the generated row id for a new record, or the existing row id for
    an exact replay (AC-004).  Raises ValueError for a conflicting re-import
    of an already-seen source_record_id (AC-005).
    """
    normalized = _normalize(record)
    try:
        _check_source_identity(conn, normalized)
    except _ExactReplay:
        existing = database.get_line_item_by_source_id(
            conn, normalized["source_record_id"]
        )
        return existing["id"]

    row_id = database.insert_line_item(conn, normalized)
    conn.commit()
    return row_id


def import_records(
    conn: sqlite3.Connection, records: List[Dict[str, Any]]
) -> List[int]:
    """Normalize and persist a list of line-item records atomically (AC-007).

    Either all newly inserted records are committed together, or none are
    persisted if any record raises an exception.  Pre-existing rows are not
    affected.

    Returns the list of generated (or existing) row ids in the same order as
    *records*.
    """
    row_ids: List[int] = []
    conn.execute("BEGIN")
    try:
        for record in records:
            normalized = _normalize(record)
            try:
                _check_source_identity(conn, normalized)
            except _ExactReplay:
                existing = database.get_line_item_by_source_id(
                    conn, normalized["source_record_id"]
                )
                row_ids.append(existing["id"])
                continue
            row_ids.append(database.insert_line_item(conn, normalized))
    except Exception:
        conn.rollback()
        raise
    conn.commit()
    return row_ids
