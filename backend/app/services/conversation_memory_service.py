import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.schedule import ScheduleResponse


class ConversationMemoryService:
    def __init__(self, path: str = "assistant_memory.db") -> None:
        self.path = Path(path)
        self._initialize()

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT latest_plan_text, latest_schedule_json, user_preferences_json
                FROM assistant_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if not row:
            return None

        latest_schedule = None
        if row["latest_schedule_json"]:
            latest_schedule = ScheduleResponse.model_validate(json.loads(row["latest_schedule_json"]))

        return {
            "latest_plan_text": row["latest_plan_text"],
            "latest_schedule": latest_schedule,
            "user_preferences": json.loads(row["user_preferences_json"] or "{}"),
        }

    def load_turns(self, session_id: str, limit: int = 30) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM assistant_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def save_session(
        self,
        session_id: str,
        latest_plan_text: str | None,
        latest_schedule: ScheduleResponse | None,
        user_preferences: dict[str, str],
    ) -> None:
        schedule_json = latest_schedule.model_dump_json() if latest_schedule else None
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO assistant_sessions (
                    session_id,
                    latest_plan_text,
                    latest_schedule_json,
                    user_preferences_json,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    latest_plan_text = excluded.latest_plan_text,
                    latest_schedule_json = excluded.latest_schedule_json,
                    user_preferences_json = excluded.user_preferences_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    latest_plan_text,
                    schedule_json,
                    json.dumps(user_preferences),
                    now,
                ),
            )

    def append_turn(self, session_id: str, role: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO assistant_messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, self._now()),
            )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assistant_sessions (
                    session_id TEXT PRIMARY KEY,
                    latest_plan_text TEXT,
                    latest_schedule_json TEXT,
                    user_preferences_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assistant_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_assistant_messages_session
                ON assistant_messages(session_id, id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
