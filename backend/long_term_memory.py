import logging
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


logger = logging.getLogger(__name__)

MemoryCategory = Literal["profile", "preference", "learning", "goal", "context"]
VALID_CATEGORIES = {"profile", "preference", "learning", "goal", "context"}

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "chat_history.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_memory(row: tuple) -> dict:
    return {
        "id": row[0],
        "user_id": row[1],
        "key": row[2],
        "value": row[3],
        "category": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def init_long_term_memory_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (user_id, key)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_user_category
            ON memories (user_id, category)
            """
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to initialize long-term memory database")
        raise
    finally:
        conn.close()


def upsert_memory(
    user_id: str,
    key: str,
    value: str,
    category: MemoryCategory,
) -> dict:
    if category not in VALID_CATEGORIES:
        raise ValueError("category is invalid")

    clean_user_id = user_id.strip()
    clean_key = key.strip().lower().replace(" ", "_")
    clean_value = value.strip()

    if not clean_user_id or not clean_key or not clean_value:
        raise ValueError("user_id, key, and value are required")

    timestamp = _now()
    memory_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO memories (id, user_id, key, value, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = excluded.updated_at
            """,
            (memory_id, clean_user_id, clean_key, clean_value, category, timestamp, timestamp),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id, user_id, key, value, category, created_at, updated_at
            FROM memories WHERE user_id = ? AND key = ?
            """,
            (clean_user_id, clean_key),
        ).fetchone()
        logger.info("Memory upserted: user_id=%s key=%s category=%s", clean_user_id, clean_key, category)
        return _row_to_memory(row)
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to upsert memory: user_id=%s key=%s", clean_user_id, clean_key)
        raise
    finally:
        conn.close()


def get_memories(
    user_id: str,
    category: MemoryCategory | None = None,
) -> list[dict]:
    conn = get_connection()
    try:
        if category is None:
            rows = conn.execute(
                """
                SELECT id, user_id, key, value, category, created_at, updated_at
                FROM memories WHERE user_id = ? ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, user_id, key, value, category, created_at, updated_at
                FROM memories WHERE user_id = ? AND category = ? ORDER BY updated_at DESC
                """,
                (user_id, category),
            ).fetchall()
        logger.info("Memories retrieved: user_id=%s category=%s count=%s", user_id, category, len(rows))
        return [_row_to_memory(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Failed to retrieve memories: user_id=%s", user_id)
        raise
    finally:
        conn.close()


def get_memory(memory_id: str, user_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, user_id, key, value, category, created_at, updated_at
            FROM memories WHERE id = ? AND user_id = ?
            """,
            (memory_id, user_id),
        ).fetchone()
        return _row_to_memory(row) if row else None
    finally:
        conn.close()


def delete_memory(memory_id: str, user_id: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM memories WHERE id = ? AND user_id = ?",
            (memory_id, user_id),
        )
        conn.commit()
        if cursor.rowcount:
            logger.info("Memory forgotten: memory_id=%s user_id=%s", memory_id, user_id)
            return True
        logger.warning("Memory not found: memory_id=%s user_id=%s", memory_id, user_id)
        return False
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to delete memory: memory_id=%s", memory_id)
        raise
    finally:
        conn.close()


def extract_memories(message: str) -> list[tuple[str, str, MemoryCategory]]:
    """Extract only explicit, durable profile and study facts from one user turn."""
    text = message.strip()
    patterns = [
        (r"\bmy name is\s+([^.!?]+)", "name", "profile"),
        (r"\bcall me\s+([^.!?]+)", "name", "profile"),
        (r"\bi (?:prefer|like)\s+([^.!?]+)", "preference", "preference"),
        (r"\bi(?: am|'m) currently learning\s+([^.!?]+)", "current_learning_focus", "learning"),
        (r"\bi(?: am|'m) learning\s+([^.!?]+)", "current_learning_focus", "learning"),
        (r"\bi(?: am|'m) preparing for\s+([^.!?]+)", "study_goal", "goal"),
        (r"\bmy goal is\s+([^.!?]+)", "study_goal", "goal"),
    ]
    extracted = []
    for pattern, key, category in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip(" ,")
            if value:
                extracted.append((key, value, category))
    return extracted


def store_extracted_memories(user_id: str, message: str) -> list[dict]:
    extracted = extract_memories(message)
    if not extracted:
        logger.info("Memory extraction skipped: user_id=%s", user_id)
        return []
    memories = [upsert_memory(user_id, key, value, category) for key, value, category in extracted]
    logger.info("Memory extraction completed: user_id=%s count=%s", user_id, len(memories))
    return memories


def get_relevant_memories(user_id: str, query: str) -> list[dict]:
    memories = get_memories(user_id)
    normalized_query = query.lower()
    if "remember" in normalized_query or "about me" in normalized_query:
        return memories
    query_words = {word for word in re.findall(r"[a-z0-9_]+", normalized_query) if len(word) > 2}
    relevant = []
    for memory in memories:
        searchable = f"{memory['key']} {memory['value']} {memory['category']}".lower()
        if any(word in searchable for word in query_words):
            relevant.append(memory)
    return relevant


def format_memory_context(memories: list[dict]) -> str:
    if not memories:
        return ""
    entries = "\n".join(f"- {item['key']}: {item['value']} ({item['category']})" for item in memories)
    return f"Relevant long-term memory for this user:\n{entries}"
