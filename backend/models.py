from pydantic import BaseModel, Field


class ChatRequest(BaseModel):

    message: str = Field(
        ...,
        min_length=1,
        description="Student's question",
    )

    conversation_id: str = "default"


class ChatResponse(BaseModel):

    response: str

    conversation_id: str

    tool_used: str | None = None

    sources: list[str] = []