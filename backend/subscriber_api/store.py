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
                    direction TEXT NOT NULL CHECK(direction IN ('enter', 'leave')),
                    source_type TEXT NOT NULL DEFAULT 'unknown',
                    publisher_id TEXT
                );

                CREATE TABLE IF NOT EXISTS rejected_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    door_id TEXT,
                    direction TEXT,
                    source_type TEXT,
                    publisher_id TEXT,
                    reason_code TEXT NOT NULL,
                    reason_message TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

                CREATE TABLE IF NOT EXISTS control_state (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    collection_enabled INTEGER NOT NULL DEFAULT 1,
                    active_source_mode TEXT NOT NULL DEFAULT 'mock',
                    baseline_occupancy INTEGER NOT NULL DEFAULT 0,
                    baseline_updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                INSERT OR IGNORE INTO state(key, value) VALUES ('occupancy', 0);
                INSERT OR IGNORE INTO control_state(
                    id,
                    collection_enabled,
                    active_source_mode,
                    baseline_occupancy,
                    baseline_updated_at,
                    updated_at
                ) VALUES (1, 1, 'mock', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """
            )
            self._migrate_legacy_schema(conn)

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        self._ensure_column(
            conn,
            table="events",
            column="source_type",
            definition="TEXT NOT NULL DEFAULT 'unknown'",
        )
        self._ensure_column(
            conn,
            table="events",
            column="publisher_id",
            definition="TEXT",
        )
        self._ensure_column(
            conn,
            table="rejected_events",
            column="source_type",
            definition="TEXT",
        )
        self._ensure_column(
            conn,
            table="rejected_events",
            column="publisher_id",
            definition="TEXT",
        )
        self._ensure_column(
            conn,
            table="rejected_events",
            column="reason_code",
            definition="TEXT NOT NULL DEFAULT 'unknown'",
        )
        self._ensure_column(
            conn,
            table="rejected_events",
            column="reason_message",
            definition="TEXT NOT NULL DEFAULT ''",
        )
        self._ensure_column(
            conn,
            table="rejected_events",
            column="payload",
            definition="TEXT NOT NULL DEFAULT '{}'",
        )
        self._ensure_column(
            conn,
            table="rejected_events",
            column="created_at",
            definition="TEXT",
        )

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(%s)" % table).fetchall()
        }
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def add_event(self, event: DoorEvent) -> Dict[str, Any]:
        with self._connect() as conn:
            control_state = self.get_control_state(conn)
            if not control_state["collection_enabled"]:
                rejected = self.record_rejected_event(
                    payload=event.to_json(),
                    reason_code="collection_paused",
                    reason_message="Collection is paused",
                    event=event,
                    conn=conn,
                )
                return {
                    "accepted": False,
                    "reason_code": "collection_paused",
                    "control_state": control_state,
                    "rejected_event": rejected,
                    "occupancy": self.get_current_occupancy(conn),
                }

            if event.source_type != "unknown" and event.source_type != control_state["active_source_mode"]:
                rejected = self.record_rejected_event(
                    payload=event.to_json(),
                    reason_code="inactive_source",
                    reason_message="Event source does not match the active source mode",
                    event=event,
                    conn=conn,
                )
                return {
                    "accepted": False,
                    "reason_code": "inactive_source",
                    "control_state": control_state,
                    "rejected_event": rejected,
                    "occupancy": self.get_current_occupancy(conn),
                }

            conn.execute(
                """
                INSERT INTO events(timestamp, door_id, direction, source_type, publisher_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event.timestamp, event.door_id, event.direction, event.source_type, event.publisher_id),
            )
            current = self.get_current_occupancy(conn)
            if event.direction == "enter":
                current += 1
            else:
                current = max(0, current - 1)
            conn.execute("UPDATE state SET value = ? WHERE key = 'occupancy'", (current,))

            return {
                "accepted": True,
                "event": event.to_dict(),
                "control_state": control_state,
                "occupancy": current,
            }

    def update_control_state(
        self,
        collection_enabled: Optional[bool] = None,
        active_source_mode: Optional[str] = None,
        baseline_occupancy: Optional[int] = None,
    ) -> Dict[str, Any]:
        updates = []
        params: List[Any] = []
        if collection_enabled is not None:
            updates.append("collection_enabled = ?")
            params.append(1 if collection_enabled else 0)
        if active_source_mode is not None:
            updates.append("active_source_mode = ?")
            params.append(active_source_mode)
        if baseline_occupancy is not None:
            updates.append("baseline_occupancy = ?")
            params.append(baseline_occupancy)
            updates.append("baseline_updated_at = CURRENT_TIMESTAMP")

        if not updates:
            return self.get_control_state()

        updates.append("updated_at = CURRENT_TIMESTAMP")

        with self._connect() as conn:
            conn.execute(f"UPDATE control_state SET {', '.join(updates)} WHERE id = 1", params)
            if baseline_occupancy is not None:
                conn.execute("UPDATE state SET value = ? WHERE key = 'occupancy'", (max(0, baseline_occupancy),))
            return self.get_control_state(conn)

    def record_error(self, payload: str, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO ingest_errors(payload, error_message) VALUES (?, ?)",
                (payload, error_message),
            )

    def record_rejected_event(
        self,
        payload: str,
        reason_code: str,
        reason_message: str,
        event: Optional[DoorEvent] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        owns_connection = conn is None
        conn = conn or self._connect()
        try:
            event_dict = event.to_dict() if event is not None else {}
            conn.execute(
                """
                INSERT INTO rejected_events(
                    timestamp, door_id, direction, source_type, publisher_id,
                    reason_code, reason_message, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_dict.get("timestamp"),
                    event_dict.get("door_id"),
                    event_dict.get("direction"),
                    event_dict.get("source_type"),
                    event_dict.get("publisher_id"),
                    reason_code,
                    reason_message,
                    payload,
                ),
            )
            row = conn.execute(
                """
                SELECT timestamp, door_id, direction, source_type, publisher_id,
                       reason_code, reason_message, payload, created_at
                FROM rejected_events
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
            return dict(row) if row else {}
        finally:
            if owns_connection:
                conn.close()

    def get_current_occupancy(self, conn: Optional[sqlite3.Connection] = None) -> int:
        owns_connection = conn is None
        conn = conn or self._connect()
        try:
            row = conn.execute("SELECT value FROM state WHERE key = 'occupancy'").fetchone()
            return int(row["value"]) if row else 0
        finally:
            if owns_connection:
                conn.close()

    def get_control_state(self, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        owns_connection = conn is None
        conn = conn or self._connect()
        try:
            row = conn.execute(
                """
                SELECT collection_enabled, active_source_mode, baseline_occupancy,
                       baseline_updated_at, updated_at
                FROM control_state
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                return {
                    "collection_enabled": True,
                    "active_source_mode": "mock",
                    "baseline_occupancy": 0,
                    "baseline_updated_at": None,
                    "updated_at": None,
                }
            return {
                "collection_enabled": bool(row["collection_enabled"]),
                "active_source_mode": row["active_source_mode"],
                "baseline_occupancy": int(row["baseline_occupancy"]),
                "baseline_updated_at": row["baseline_updated_at"],
                "updated_at": row["updated_at"],
            }
        finally:
            if owns_connection:
                conn.close()

    def list_events(
        self,
        limit: int = 50,
        door_id: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        direction: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self._list_event_rows(
            table="events",
            limit=limit,
            door_id=door_id,
            since=since,
            until=until,
            direction=direction,
            source_type=source_type,
        )

    def list_rejected_events(
        self,
        limit: int = 50,
        door_id: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        direction: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self._list_event_rows(
            table="rejected_events",
            limit=limit,
            door_id=door_id,
            since=since,
            until=until,
            direction=direction,
            source_type=source_type,
        )

    def _list_event_rows(
        self,
        table: str,
        limit: int,
        door_id: Optional[str],
        since: Optional[str],
        until: Optional[str],
        direction: Optional[str],
        source_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        query = (
            "SELECT timestamp, door_id, direction, source_type, publisher_id"
            + (", reason_code, reason_message, payload, created_at" if table == "rejected_events" else "")
            + f" FROM {table}"
        )
        clauses: List[str] = []
        params: List[Any] = []
        if door_id:
            clauses.append("door_id = ?")
            params.append(door_id)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        if until:
            clauses.append("timestamp <= ?")
            params.append(until)
        if direction:
            clauses.append("direction = ?")
            params.append(direction)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            control_state = self.get_control_state(conn)
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
            bucket_rows = conn.execute(
                """
                SELECT
                    substr(timestamp, 1, 16) || ':00Z' AS bucket,
                    SUM(CASE WHEN direction = 'enter' THEN 1 ELSE 0 END) AS enters,
                    SUM(CASE WHEN direction = 'leave' THEN 1 ELSE 0 END) AS leaves
                FROM events
                WHERE replace(substr(timestamp, 1, 19), 'T', ' ') >= ?
                GROUP BY bucket
                ORDER BY bucket ASC
                """
            , (control_state["baseline_updated_at"],)).fetchall()
            recent_rejected = conn.execute("SELECT COUNT(*) AS count FROM rejected_events").fetchone()
            accepted_count = conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()

            occupancy_timeline = []
            running = control_state["baseline_occupancy"]
            for row in bucket_rows:
                running = max(0, running + int(row["enters"] or 0) - int(row["leaves"] or 0))
                occupancy_timeline.append({"bucket": row["bucket"], "occupancy": running})

            return {
                "occupancy": self.get_current_occupancy(conn),
                "total_enters": int(totals["enters"] or 0),
                "total_leaves": int(totals["leaves"] or 0),
                "per_door": [
                    {
                        "door_id": row["door_id"],
                        "enters": int(row["enters"] or 0),
                        "leaves": int(row["leaves"] or 0),
                        "net": int(row["enters"] or 0) - int(row["leaves"] or 0),
                    }
                    for row in door_rows
                ],
                "entries_vs_leaves": [
                    {
                        "bucket": row["bucket"],
                        "enters": int(row["enters"] or 0),
                        "leaves": int(row["leaves"] or 0),
                    }
                    for row in bucket_rows
                ],
                "occupancy_timeline": occupancy_timeline,
                "system_status": {
                    "accepted_events": int(accepted_count["count"] or 0),
                    "rejected_events": int(recent_rejected["count"] or 0),
                    "collection_enabled": control_state["collection_enabled"],
                    "active_source_mode": control_state["active_source_mode"],
                },
                "control_state": control_state,
            }
