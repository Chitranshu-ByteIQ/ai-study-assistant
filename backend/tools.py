from contextvars import ContextVar, Token
from typing import Literal

from langchain_core.tools import tool

from backend.reminders import (
    complete_reminder as complete_reminder_record,
    create_reminder as create_reminder_record,
    delete_reminder as delete_reminder_record,
    get_reminder as get_reminder_record,
    get_reminders as get_reminder_records,
    update_reminder as update_reminder_record,
)
from backend.vector_store import retriever


@tool
def search_course_material(query: str) -> str:
    """
    Search the student's course material.

    Use this tool when the student asks about
    course concepts, lectures, notes, RAG,
    embeddings, vector databases, LangChain,
    LangGraph, or other topics that should be
    answered from the student's course material.
    """

    documents = retriever.invoke(query)

    if not documents:

        return (
            "No relevant course material was found."
        )

    results = []

    for document in documents:

        source = document.metadata.get(
            "source",
            "unknown",
        )

        results.append(
            f"""
Source: {source}

Content:
{document.page_content}
"""
        )

    return "\n\n".join(results)


# ============================================================
# REMINDER TOOLS
# ============================================================

_active_conversation_id: ContextVar[str | None] = ContextVar(
    "active_conversation_id",
    default=None,
)


def set_active_conversation(conversation_id: str) -> Token:
    return _active_conversation_id.set(conversation_id)


def reset_active_conversation(token: Token) -> None:
    _active_conversation_id.reset(token)


def _conversation_id() -> str:
    conversation_id = _active_conversation_id.get()

    if not conversation_id:
        raise ValueError("The active conversation is missing")

    return conversation_id


def _belongs_to_active_conversation(reminder_id: str) -> bool:
    reminder = get_reminder_record(reminder_id)

    return (
        reminder is not None
        and reminder["conversation_id"] == _conversation_id()
    )


def _format_reminder(reminder: dict) -> str:
    return (
        f"ID: {reminder['id']} | Task: {reminder['reminder_text']} | "
        f"Due: {reminder['due_at']} | Status: {reminder['status']}"
    )


@tool
def create_reminder(
    reminder_text: str,
    due_at: str,
) -> str:
    """Create a reminder for the active chat conversation.

    due_at must be a complete ISO 8601 datetime, for example
    2026-09-18T19:00:00+05:30. Ask a clarification question when a user has
    not supplied a date and time.
    """
    try:
        reminder = create_reminder_record(
            conversation_id=_conversation_id(),
            reminder_text=reminder_text,
            due_at=due_at,
        )
        return f"Reminder created. {_format_reminder(reminder)}"
    except ValueError as error:
        return f"I could not create the reminder: {error}"


@tool
def get_reminders(
    status: Literal["pending", "completed", "cancelled", "overdue"] | None = None,
) -> str:
    """List reminders for the active chat conversation, optionally by status."""
    reminders = get_reminder_records(
        conversation_id=_conversation_id(),
        status=status,
    )

    if not reminders:
        return "No reminders were found for this conversation."

    return "\n".join(_format_reminder(reminder) for reminder in reminders)


@tool
def update_reminder(
    reminder_id: str,
    reminder_text: str | None = None,
    due_at: str | None = None,
    status: Literal["pending", "completed", "cancelled", "overdue"] | None = None,
) -> str:
    """Update a reminder by ID. Supply one or more fields to change.

    due_at, if supplied, must be a complete ISO 8601 datetime.
    """
    if not _belongs_to_active_conversation(reminder_id):
        return f"No reminder was found with ID {reminder_id} in this conversation."

    try:
        reminder = update_reminder_record(
            reminder_id=reminder_id,
            reminder_text=reminder_text,
            due_at=due_at,
            status=status,
        )
    except ValueError as error:
        return f"I could not update the reminder: {error}"

    if reminder is None:
        return f"No reminder was found with ID {reminder_id}."

    return f"Reminder updated. {_format_reminder(reminder)}"


@tool
def delete_reminder(reminder_id: str) -> str:
    """Delete a reminder by ID."""
    if not _belongs_to_active_conversation(reminder_id):
        return f"No reminder was found with ID {reminder_id} in this conversation."

    if not delete_reminder_record(reminder_id):
        return f"No reminder was found with ID {reminder_id} in this conversation."

    return f"Reminder deleted: {reminder_id}."


@tool
def complete_reminder(reminder_id: str) -> str:
    """Mark a reminder as completed by ID."""
    if not _belongs_to_active_conversation(reminder_id):
        return f"No reminder was found with ID {reminder_id} in this conversation."

    reminder = complete_reminder_record(reminder_id)

    if reminder is None:
        return f"No reminder was found with ID {reminder_id}."

    return f"Reminder completed. {_format_reminder(reminder)}"

