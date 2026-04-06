from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.common.events import DoorEvent


class EventStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    door_id TEXT NOT NULL,
                    direction TEXT NOT NULL CHECK(direction IN ('enter', 'leave'))
                );

                CREATE TABLE IF NOT EXISTS ingest_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );

                INSERT OR IGNORE INTO state(key, value) VALUES ('occupancy', 0);
                """
            )

    def add_event(self, event: DoorEvent) -> int:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events(timestamp, door_id, direction) VALUES (?, ?, ?)",
                (event.timestamp, event.door_id, event.direction),
            )
            current = self.get_current_occupancy(conn)
            if event.direction == "enter":
                current += 1
            else:
                current = max(0, current - 1)
            conn.execute("UPDATE state SET value = ? WHERE key = 'occupancy'", (current,))
            return current

    def record_error(self, payload: str, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO ingest_errors(payload, error_message) VALUES (?, ?)",
                (payload, error_message),
            )

    def get_current_occupancy(self, conn: Optional[sqlite3.Connection] = None) -> int:
        owns_connection = conn is None
        conn = conn or self._connect()
        try:
            row = conn.execute("SELECT value FROM state WHERE key = 'occupancy'").fetchone()
            return int(row["value"]) if row else 0
        finally:
            if owns_connection:
                conn.close()

    def list_events(
        self, limit: int = 50, door_id: Optional[str] = None, since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT timestamp, door_id, direction FROM events"
        clauses = []
        params: list[Any] = []
        if door_id:
            clauses.append("door_id = ?")
            params.append(door_id)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN direction = 'enter' THEN 1 ELSE 0 END) AS enters,
                    SUM(CASE WHEN direction = 'leave' THEN 1 ELSE 0 END) AS leaves
                FROM events
                """
            ).fetchone()
            door_rows = conn.execute(
                """
                SELECT
                    door_id,
                    SUM(CASE WHEN direction = 'enter' THEN 1 ELSE 0 END) AS enters,
                    SUM(CASE WHEN direction = 'leave' THEN 1 ELSE 0 END) AS leaves
                FROM events
                GROUP BY door_id
                ORDER BY door_id ASC
                """
            ).fetchall()
            return {
                "occupancy": self.get_current_occupancy(conn),
                "total_enters": int(totals["enters"] or 0),
                "total_leaves": int(totals["leaves"] or 0),
                "per_door": [dict(row) for row in door_rows],
            }

