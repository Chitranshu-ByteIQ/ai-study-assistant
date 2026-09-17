import sqlite3
import uuid
from pathlib import Path

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "chat_history.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # Threads table
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # Messages table
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (conversation_id)
            REFERENCES threads(id)
        )
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# CREATE THREAD
# ============================================================

def create_thread(title: str = "New Chat"):

    conversation_id = str(uuid.uuid4())

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO threads (id, title)
        VALUES (?, ?)
        """,
        (
            conversation_id,
            title,
        ),
    )

    conn.commit()
    conn.close()

    return conversation_id


# ============================================================
# GET ALL THREADS
# ============================================================

def get_threads():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at
        FROM threads
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "conversation_id": row[0],
            "title": row[1],
            "created_at": row[2],
        }
        for row in rows
    ]


# ============================================================
# GET SINGLE THREAD
# ============================================================

def get_thread(conversation_id: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at
        FROM threads
        WHERE id = ?
        """,
        (conversation_id,),
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return {
        "conversation_id": row[0],
        "title": row[1],
        "created_at": row[2],
    }


# ============================================================
# SAVE MESSAGE
# ============================================================

def save_message(
    conversation_id: str,
    role: str,
    content: str,
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages
        (
            conversation_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content,
        ),
    )

    conn.commit()
    conn.close()


# ============================================================
# GET CONVERSATION HISTORY
# ============================================================

def get_history(
    conversation_id: str,
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id
        """,
        (conversation_id,),
    )

    rows = cursor.fetchall()

    conn.close()

    messages = []

    for role, content in rows:

        if role == "user":

            messages.append(
                HumanMessage(
                    content=content
                )
            )

        elif role == "assistant":

            messages.append(
                AIMessage(
                    content=content
                )
            )

    return messages


# ============================================================
# GET RAW MESSAGES
# ============================================================

def get_messages(conversation_id: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id
        """,
        (conversation_id,),
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]

# ============================================================
# GET ALL THREADS
# ============================================================

def get_all_threads():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at
        FROM threads
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "conversation_id": row[0],
            "title": row[1],
            "created_at": row[2],
        }
        for row in rows
    ]


# ============================================================
# GET SINGLE THREAD
# ============================================================

def get_thread(conversation_id: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at
        FROM threads
        WHERE id = ?
        """,
        (conversation_id,),
    )

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "conversation_id": row[0],
        "title": row[1],
        "created_at": row[2],
    }

# ============================================================
# DELETE THREAD
# ============================================================

def delete_thread(conversation_id: str):

    conn = get_connection()
    cursor = conn.cursor()

    # Delete messages first
    cursor.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,),
    )

    # Delete thread
    cursor.execute(
        """
        DELETE FROM threads
        WHERE id = ?
        """,
        (conversation_id,),
    )

    conn.commit()

    deleted = cursor.rowcount

    conn.close()

    return deleted > 0


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()