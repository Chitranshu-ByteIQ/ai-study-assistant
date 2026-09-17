import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

ReminderStatus = Literal["pending", "completed", "cancelled", "overdue"]
VALID_STATUSES = {"pending", "completed", "cancelled", "overdue"}

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "chat_history.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_due_at(due_at: str) -> str:
    value = due_at.strip()

    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"

    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError("due_at must be a valid ISO 8601 datetime") from error


def _is_past_due(due_at: str) -> bool:
    due = datetime.fromisoformat(due_at)

    if due.tzinfo is None:
        return due < datetime.now()

    return due.astimezone(timezone.utc) < datetime.now(timezone.utc)


def _row_to_reminder(row: tuple) -> dict:
    return {
        "id": row[0],
        "conversation_id": row[1],
        "reminder_text": row[2],
        "due_at": row[3],
        "status": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def init_reminders_db() -> None:
    conn = get_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                reminder_text TEXT NOT NULL,
                due_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES threads(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reminders_conversation_status_due
            ON reminders (conversation_id, status, due_at)
            """
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to initialize reminder database")
        raise
    finally:
        conn.close()


def _refresh_overdue_reminders(
    conn: sqlite3.Connection,
    conversation_id: str | None = None,
) -> None:
    query = "SELECT id, due_at FROM reminders WHERE status = 'pending'"
    params: tuple[str, ...] = ()

    if conversation_id is not None:
        query += " AND conversation_id = ?"
        params = (conversation_id,)

    overdue_ids = [
        row[0]
        for row in conn.execute(query, params).fetchall()
        if _is_past_due(row[1])
    ]

    if overdue_ids:
        conn.executemany(
            """
            UPDATE reminders
            SET status = 'overdue', updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            [(_now(), reminder_id) for reminder_id in overdue_ids],
        )


def create_reminder(
    conversation_id: str,
    reminder_text: str,
    due_at: str,
) -> dict:
    normalized_due_at = _normalize_due_at(due_at)
    cleaned_text = reminder_text.strip()

    if not conversation_id.strip():
        raise ValueError("conversation_id is required")
    if not cleaned_text:
        raise ValueError("reminder_text is required")

    reminder_id = str(uuid.uuid4())
    timestamp = _now()
    reminder = {
        "id": reminder_id,
        "conversation_id": conversation_id,
        "reminder_text": cleaned_text,
        "due_at": normalized_due_at,
        "status": "pending",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO reminders (
                id, conversation_id, reminder_text, due_at,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(reminder.values()),
        )
        conn.commit()
        logger.info(
            "Reminder created: reminder_id=%s conversation_id=%s",
            reminder_id,
            conversation_id,
        )
        return reminder
    except sqlite3.Error:
        conn.rollback()
        logger.exception(
            "Failed to create reminder: conversation_id=%s", conversation_id
        )
        raise
    finally:
        conn.close()


def get_reminder(reminder_id: str) -> dict | None:
    conn = get_connection()

    try:
        _refresh_overdue_reminders(conn)
        row = conn.execute(
            """
            SELECT id, conversation_id, reminder_text, due_at,
                   status, created_at, updated_at
            FROM reminders WHERE id = ?
            """,
            (reminder_id,),
        ).fetchone()
        conn.commit()

        if row is None:
            logger.warning("Reminder not found: reminder_id=%s", reminder_id)
            return None

        logger.info("Reminder retrieved: reminder_id=%s", reminder_id)
        return _row_to_reminder(row)
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to retrieve reminder: reminder_id=%s", reminder_id)
        raise
    finally:
        conn.close()


def get_reminders(
    conversation_id: str | None = None,
    status: ReminderStatus | None = None,
) -> list[dict]:
    conn = get_connection()

    try:
        _refresh_overdue_reminders(conn, conversation_id)
        query = """
            SELECT id, conversation_id, reminder_text, due_at,
                   status, created_at, updated_at
            FROM reminders
        """
        conditions = []
        params = []

        if conversation_id is not None:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY due_at ASC, created_at ASC"
        rows = conn.execute(query, tuple(params)).fetchall()
        conn.commit()
        logger.info(
            "Reminders retrieved: conversation_id=%s status=%s count=%s",
            conversation_id,
            status,
            len(rows),
        )
        return [_row_to_reminder(row) for row in rows]
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to retrieve reminders")
        raise
    finally:
        conn.close()


def update_reminder(
    reminder_id: str,
    reminder_text: str | None = None,
    due_at: str | None = None,
    status: ReminderStatus | None = None,
) -> dict | None:
    if reminder_text is not None:
        cleaned_text = reminder_text.strip()
        if not cleaned_text:
            raise ValueError("reminder_text cannot be empty")
    else:
        cleaned_text = None

    if due_at is not None:
        normalized_due_at = _normalize_due_at(due_at)
    else:
        normalized_due_at = None

    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError("status is invalid")
    if (
        cleaned_text is None
        and normalized_due_at is None
        and status is None
    ):
        raise ValueError("At least one field must be supplied for update")

    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            UPDATE reminders
            SET reminder_text = CASE WHEN ? THEN ? ELSE reminder_text END,
                due_at = CASE WHEN ? THEN ? ELSE due_at END,
                status = CASE WHEN ? THEN ? ELSE status END,
                updated_at = ?
            WHERE id = ?
            """,
            (
                cleaned_text is not None,
                cleaned_text,
                normalized_due_at is not None,
                normalized_due_at,
                status is not None,
                status,
                _now(),
                reminder_id,
            ),
        )
        conn.commit()

        if cursor.rowcount == 0:
            logger.warning("Reminder not found: reminder_id=%s", reminder_id)
            return None

        logger.info("Reminder updated: reminder_id=%s", reminder_id)
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to update reminder: reminder_id=%s", reminder_id)
        raise
    finally:
        conn.close()

    return get_reminder(reminder_id)


def complete_reminder(reminder_id: str) -> dict | None:
    return update_reminder(reminder_id, status="completed")


def delete_reminder(reminder_id: str) -> bool:
    conn = get_connection()

    try:
        cursor = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()

        if cursor.rowcount == 0:
            logger.warning("Reminder not found: reminder_id=%s", reminder_id)
            return False

        logger.info("Reminder deleted: reminder_id=%s", reminder_id)
        return True
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to delete reminder: reminder_id=%s", reminder_id)
        raise
    finally:
        conn.close()


def delete_reminders_for_conversation(conversation_id: str) -> int:
    conn = get_connection()

    try:
        cursor = conn.execute(
            "DELETE FROM reminders WHERE conversation_id = ?", (conversation_id,)
        )
        conn.commit()
        logger.info(
            "Conversation reminders deleted: conversation_id=%s count=%s",
            conversation_id,
            cursor.rowcount,
        )
        return cursor.rowcount
    except sqlite3.Error:
        conn.rollback()
        logger.exception(
            "Failed to delete conversation reminders: conversation_id=%s",
            conversation_id,
        )
        raise
    finally:
        conn.close()
