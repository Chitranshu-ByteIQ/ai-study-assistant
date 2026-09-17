from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from backend.models import (
    ChatRequest,
    ChatResponse,
    ThreadCreateRequest,
    ThreadResponse,
)

from backend.agent import graph
from backend.tools import (
    reset_active_conversation,
    set_active_conversation,
)

from backend.memory import (
    create_thread,
    get_all_threads,
    get_thread,
    get_history,
    get_messages,
    save_message,
    delete_thread,
)
from backend.long_term_memory import (
    format_memory_context,
    get_relevant_memories,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

UserIdHeader = Annotated[
    str | None,
    Header(
        alias="X-User-ID",
        description="Optional stable user identifier used for cross-thread long-term memory.",
    ),
]


# ============================================================
# CREATE NEW THREAD
# ============================================================

@router.post(
    "/threads",
    response_model=ThreadResponse,
    summary="Create a chat thread",
    description="Create a conversation before sending messages to POST /chat/.",
)
async def create_new_thread(
    request: ThreadCreateRequest,
):

    conversation_id = create_thread(
        title=request.title
    )

    thread = get_thread(
        conversation_id
    )

    return thread


# ============================================================
# GET ALL THREADS
# ============================================================

@router.get(
    "/threads",
    response_model=list[ThreadResponse],
    summary="List chat threads",
)
async def list_threads():

    return get_all_threads()


# ============================================================
# GET / RESUME THREAD
# ============================================================

@router.get(
    "/threads/{conversation_id}",
    summary="Get a thread and its persisted messages",
    responses={404: {"description": "Conversation not found"}},
)
async def resume_thread(
    conversation_id: str,
):

    thread = get_thread(
        conversation_id
    )

    if not thread:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    messages = get_messages(
        conversation_id
    )

    return {
        "thread": thread,
        "messages": messages,
    }


# ============================================================
# DELETE THREAD
# ============================================================

@router.delete(
    "/threads/{conversation_id}",
    summary="Delete a chat thread",
    responses={404: {"description": "Conversation not found"}},
)
async def remove_thread(
    conversation_id: str,
):

    deleted = delete_thread(
        conversation_id
    )

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return {
        "message": "Conversation deleted",
        "conversation_id": conversation_id,
    }


# ============================================================
# CHAT
# ============================================================

@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send a message to a chat thread",
    description="Loads thread history, adds relevant long-term memory for X-User-ID, then invokes the LangGraph agent.",
    responses={404: {"description": "Conversation not found"}},
)
async def chat(
    request: ChatRequest,
    user_id: UserIdHeader = None,
):

    try:

        # ----------------------------------------------------
        # Check whether conversation exists
        # ----------------------------------------------------

        thread = get_thread(
            request.conversation_id
        )

        if not thread:

            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        # ----------------------------------------------------
        # Load previous conversation
        # ----------------------------------------------------

        history = get_history(
            request.conversation_id
        )

        memory_context = ""
        if user_id:
            memory_context = format_memory_context(
                get_relevant_memories(user_id, request.message)
            )

        # ----------------------------------------------------
        # Add current user message
        # ----------------------------------------------------

        messages = history + [
            {
                "role": "user",
                "content": request.message,
            }
        ]

        # ----------------------------------------------------
        # Run LangGraph
        # ----------------------------------------------------

        conversation_token = set_active_conversation(
            request.conversation_id
        )

        try:
            result = graph.invoke(
                {
                    "messages": messages,
                    "iteration": 0,
                    "user_id": user_id,
                    "memory_context": memory_context,
                }
            )
        finally:
            reset_active_conversation(conversation_token)

        # ----------------------------------------------------
        # Get final response
        # ----------------------------------------------------

        final_message = result["messages"][-1]

        response = final_message.content

        # ----------------------------------------------------
        # Detect tool usage
        # ----------------------------------------------------

        tool_used = None
        sources = []

        for message in result["messages"]:

            if message.type == "tool":

                tool_used = message.name

                content = message.content

                if "Source:" in content:

                    parts = content.split(
                        "Source:"
                    )

                    for part in parts[1:]:

                        source = (
                            part
                            .split("\n")[0]
                            .strip()
                        )

                        if source:

                            sources.append(
                                source
                            )

        # ----------------------------------------------------
        # Save user message
        # ----------------------------------------------------

        save_message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message,
        )

        # ----------------------------------------------------
        # Save assistant response
        # ----------------------------------------------------

        save_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=response,
        )

        # ----------------------------------------------------
        # Return response
        # ----------------------------------------------------

        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id,
            tool_used=tool_used,
            sources=list(
                dict.fromkeys(sources)
            ),
        )

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
