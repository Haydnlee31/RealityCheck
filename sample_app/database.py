"""
Thin SQLite persistence layer for retail transaction line items.
"""

import sqlite3
from typing import Any, Dict, List, Optional


def connect(db_path: str) -> sqlite3.Connection:
    """Return a connection to the SQLite database at *db_path*.

    The caller is responsible for closing the connection.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the line_items table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS line_items (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            source_record_id TEXT    NOT NULL,
            invoice_no       TEXT    NOT NULL,
            stock_code       TEXT    NOT NULL,
            quantity         INTEGER NOT NULL,
            unit_price       REAL    NOT NULL
        )
        """
    )
    conn.commit()


def get_line_item_by_source_id(
    conn: sqlite3.Connection, source_record_id: str
) -> Optional[Dict[str, Any]]:
    """Return the stored line item for *source_record_id*, or None if absent."""
    cursor = conn.execute(
        "SELECT * FROM line_items WHERE source_record_id = ?",
        (source_record_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row is not None else None


def insert_line_item(conn: sqlite3.Connection, record: Dict[str, Any]) -> int:
    """Insert one line-item record and return its generated row id.

    Does NOT commit.  The caller is responsible for committing or rolling back
    the enclosing transaction.
    """
    cursor = conn.execute(
        """
        INSERT INTO line_items
            (source_record_id, invoice_no, stock_code, quantity, unit_price)
        VALUES
            (:source_record_id, :invoice_no, :stock_code, :quantity, :unit_price)
        """,
        record,
    )
    return cursor.lastrowid


def get_line_items_by_invoice(
    conn: sqlite3.Connection, invoice_no: str
) -> List[Dict[str, Any]]:
    """Return all line items whose invoice_no matches *invoice_no* exactly."""
    cursor = conn.execute(
        "SELECT * FROM line_items WHERE invoice_no = ?",
        (invoice_no,),
    )
    return [dict(row) for row in cursor.fetchall()]
