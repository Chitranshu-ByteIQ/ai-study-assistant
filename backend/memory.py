import sqlite3

from pathlib import Path

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)


DB_PATH = Path("chat_history.db")


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# SAVE MESSAGE
# ============================================================

def save_message(
    conversation_id: str,
    role: str,
    content: str,
):

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content)
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
# GET CONVERSATION
# ============================================================

def get_history(
    conversation_id: str,
):

    conn = sqlite3.connect(DB_PATH)

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
# INITIALIZE
# ============================================================

init_db()