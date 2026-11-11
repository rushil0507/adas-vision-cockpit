"""SQLite Database storage for ADAS alert and event logging."""

import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "adas_events.db",
)


class EventDatabase:
    """Manages SQLite storage for ADAS alerts, incidents, and events."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates the events table and indexes if not already present."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    snapshot_path TEXT
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity)"
            )
            conn.commit()

    def log_event(
        self,
        alert_type: str,
        severity: str,
        message: str,
        snapshot_path: Optional[str] = None,
    ) -> int:
        """Inserts a new alert event into SQLite."""
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (timestamp, alert_type, severity, message, snapshot_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, alert_type, severity, message, snapshot_path),
            )
            conn.commit()
            return cursor.lastrowid

    def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves paginated events ordered by timestamp descending."""
        query = "SELECT id, timestamp, alert_type, severity, message, snapshot_path FROM events"
        params: List[Any] = []

        if severity:
            query += " WHERE severity = ?"
            params.append(severity.upper())

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_event_count(self, severity: Optional[str] = None) -> int:
        """Returns total number of events."""
        query = "SELECT COUNT(*) FROM events"
        params: List[Any] = []
        if severity:
            query += " WHERE severity = ?"
            params.append(severity.upper())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return int(cursor.fetchone()[0])
