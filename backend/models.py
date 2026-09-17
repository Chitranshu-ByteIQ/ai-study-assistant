from pydantic import BaseModel, Field


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