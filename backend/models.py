from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ============================================================
# CHAT
# ============================================================

class ChatRequest(BaseModel):

    message: str = Field(
        ...,
        min_length=1,
        description="Student's question",
    )

    conversation_id: str


class ChatResponse(BaseModel):

    response: str

    conversation_id: str

    tool_used: str | None = None

    sources: list[str] = []


# ============================================================
# THREAD
# ============================================================

class ThreadCreateRequest(BaseModel):

    title: str = "New Chat"


class ThreadResponse(BaseModel):

    conversation_id: str

    title: str

    created_at: str


class MessageResponse(BaseModel):

    id: int

    role: str

    content: str

    created_at: str


# ============================================================
# REMINDERS
# ============================================================

ReminderStatus = Literal[
    "pending",
    "completed",
    "cancelled",
    "overdue",
]


class ReminderCreateRequest(BaseModel):

    conversation_id: str = Field(..., min_length=1)

    reminder_text: str = Field(..., min_length=1)

    due_at: datetime


class ReminderUpdateRequest(BaseModel):

    reminder_text: str | None = Field(default=None, min_length=1)

    due_at: datetime | None = None

    status: ReminderStatus | None = None

    @model_validator(mode="after")
    def requires_update(self):

        if (
            self.reminder_text is None
            and self.due_at is None
            and self.status is None
        ):
            raise ValueError("At least one field must be supplied for update")

        return self


class ReminderResponse(BaseModel):

    id: str

    conversation_id: str

    reminder_text: str

    due_at: datetime

    status: ReminderStatus

    created_at: datetime

    updated_at: datetime


# ============================================================
# LONG-TERM MEMORY
# ============================================================

MemoryCategory = Literal["profile", "preference", "learning", "goal", "context"]


class MemoryCreateRequest(BaseModel):

    key: str = Field(
        ...,
        min_length=1,
        description="Stable fact name. Reusing it updates the existing global memory.",
        examples=["preferred_explanation_style"],
    )
    value: str = Field(
        ...,
        min_length=1,
        description="Durable fact to retain.",
        examples=["beginner-friendly"],
    )
    category: MemoryCategory = Field(
        ...,
        description="Classification used for display and filtering.",
        examples=["preference"],
    )


class MemoryResponse(BaseModel):

    id: str = Field(description="Unique persistent memory identifier.")
    key: str = Field(description="Stable memory key.", examples=["name"])
    value: str = Field(description="Stored durable fact.", examples=["Chitranshu"])
    category: MemoryCategory = Field(description="Memory classification.")
    created_at: datetime = Field(description="UTC creation timestamp.")
    updated_at: datetime = Field(description="UTC timestamp of the latest change.")


class MemoryDeleteResponse(BaseModel):

    message: str = Field(examples=["Memory forgotten"])
    memory_id: str = Field(description="Identifier of the removed memory.")
