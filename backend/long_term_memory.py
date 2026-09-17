import logging
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


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
        "key": row[1],
        "value": row[2],
        "category": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }


def init_long_term_memory_db() -> None:
    conn = get_connection()
    try:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(memories)").fetchall()
        }

        if columns and "user_id" in columns:
            conn.execute(
                """
                CREATE TABLE memories_global (
                    id TEXT PRIMARY KEY,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO memories_global (id, key, value, category, created_at, updated_at)
                SELECT id, key, value, category, created_at, updated_at
                FROM (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY key ORDER BY updated_at DESC, rowid DESC
                    ) AS row_number
                    FROM memories
                )
                WHERE row_number = 1
                """
            )
            conn.execute("DROP TABLE memories")
            conn.execute("ALTER TABLE memories_global RENAME TO memories")

        conn.execute("DROP INDEX IF EXISTS idx_memories_user_category")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_category
            ON memories (category)
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
    key: str,
    value: str,
    category: MemoryCategory,
) -> dict:
    if category not in VALID_CATEGORIES:
        raise ValueError("category is invalid")

    clean_key = key.strip().lower().replace(" ", "_")
    clean_value = value.strip()

    if not clean_key or not clean_value:
        raise ValueError("key and value are required")

    timestamp = _now()
    memory_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO memories (id, key, value, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = excluded.updated_at
            """,
            (memory_id, clean_key, clean_value, category, timestamp, timestamp),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id, key, value, category, created_at, updated_at
            FROM memories WHERE key = ?
            """,
            (clean_key,),
        ).fetchone()
        logger.info("Memory upserted: key=%s category=%s", clean_key, category)
        return _row_to_memory(row)
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to upsert memory: key=%s", clean_key)
        raise
    finally:
        conn.close()


def get_memories(
    category: MemoryCategory | None = None,
) -> list[dict]:
    conn = get_connection()
    try:
        if category is None:
            rows = conn.execute(
                """
                SELECT id, key, value, category, created_at, updated_at
                FROM memories ORDER BY updated_at DESC
                """,
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, key, value, category, created_at, updated_at
                FROM memories WHERE category = ? ORDER BY updated_at DESC
                """,
                (category,),
            ).fetchall()
        logger.info("Memories retrieved: category=%s count=%s", category, len(rows))
        return [_row_to_memory(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Failed to retrieve memories")
        raise
    finally:
        conn.close()


def get_memory(memory_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, key, value, category, created_at, updated_at
            FROM memories WHERE id = ?
            """,
            (memory_id,),
        ).fetchone()
        return _row_to_memory(row) if row else None
    finally:
        conn.close()


def delete_memory(memory_id: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,),
        )
        conn.commit()
        if cursor.rowcount:
            logger.info("Memory forgotten: memory_id=%s", memory_id)
            return True
        logger.warning("Memory not found: memory_id=%s", memory_id)
        return False
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to delete memory: memory_id=%s", memory_id)
        raise
    finally:
        conn.close()


class MemoryAction(BaseModel):
    action: Literal["upsert", "delete"]
    key: str = Field(min_length=1)
    value: str | None = None
    category: MemoryCategory = "context"


class MemoryExtraction(BaseModel):
    actions: list[MemoryAction] = Field(default_factory=list)


def _fallback_extract_memories(message: str) -> list[MemoryAction]:
    """Keep explicit durable facts usable if the extractor is unavailable."""
    text = message.strip()
    patterns = [
        (r"\bmy name is\s+([A-Za-z][^.!?]*?)(?=\s+and\s+i(?:'m| am)\b|[.!?]|$)", "name", "profile"),
        (r"\bcall me\s+([A-Za-z][^.!?]*?)(?=\s+and\s+i(?:'m| am)\b|[.!?]|$)", "name", "profile"),
        (r"\bi am\s+(\d{1,3})\s+years? old\b", "age", "profile"),
        (r"\bi['’]?m\s+(\d{1,3})\s+years? old\b", "age", "profile"),
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
                extracted.append(MemoryAction(action="upsert", key=key, value=value, category=category))
    return extracted


def _extract_memory_actions(message: str, existing: list[dict]) -> list[MemoryAction]:
    from langchain_groq import ChatGroq

    from backend.config import settings

    extractor = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
    ).with_structured_output(MemoryExtraction)
    existing_context = json.dumps(
        [{"key": item["key"], "value": item["value"], "category": item["category"]} for item in existing],
        separators=(",", ":"),
    )
    prompt = (
        "Extract only explicit durable user facts from the latest message. "
        "Ignore questions, tasks, course content, and casual statements. "
        "Use stable canonical keys so changed facts update existing entries. "
        "Return upsert for new or changed facts, delete only when the user clearly retracts a fact. "
        "Return no actions for irrelevant text. Existing global memories: "
        f"{existing_context}\nLatest user message: {message}"
    )
    result = extractor.invoke(prompt)
    return result.actions


def store_extracted_memories(message: str) -> list[dict]:
    existing = get_memories()
    try:
        actions = _extract_memory_actions(message, existing)
    except Exception:
        logger.exception("Memory extraction failed; using explicit fallback")
        actions = _fallback_extract_memories(message)

    memories = []
    for action in actions:
        key = action.key.strip().lower().replace(" ", "_")
        if action.action == "delete":
            if delete_memory_by_key(key):
                continue
        if action.value and action.value.strip():
            memories.append(upsert_memory(key, action.value, action.category))
    logger.info("Memory extraction completed: count=%s", len(memories))
    return memories


def get_relevant_memories(query: str) -> list[dict]:
    memories = get_memories()
    normalized_query = query.lower()
    if (
        "remember" in normalized_query
        or "about me" in normalized_query
        or re.search(r"\b(my|me|i|i'm|am i)\b", normalized_query)
    ):
        return memories
    query_words = {word for word in re.findall(r"[a-z0-9_]+", normalized_query) if len(word) > 2}
    relevant = []
    for memory in memories:
        searchable = f"{memory['key']} {memory['value']} {memory['category']}".lower()
        if any(word in searchable for word in query_words):
            relevant.append(memory)
    return relevant


def delete_memory_by_key(key: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        conn.rollback()
        logger.exception("Failed to delete memory by key: key=%s", key)
        raise
    finally:
        conn.close()


def format_memory_context(memories: list[dict]) -> str:
    if not memories:
        return ""
    entries = "\n".join(f"- {item['key']}: {item['value']} ({item['category']})" for item in memories)
    return f"Relevant global long-term memory:\n{entries}"
