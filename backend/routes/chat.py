from fastapi import APIRouter, HTTPException

from backend.models import (
    ChatRequest,
    ChatResponse,
    ThreadCreateRequest,
    ThreadResponse,
    MessageResponse,
)

from backend.agent import graph

from backend.memory import (
    create_thread,
    get_threads,
    get_thread,
    get_history,
    get_messages,
    save_message,
    delete_thread,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


# ============================================================
# CREATE NEW THREAD
# ============================================================

@router.post(
    "/threads",
    response_model=ThreadResponse,
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
)
async def list_threads():

    return get_threads()


# ============================================================
# GET / RESUME THREAD
# ============================================================

@router.get(
    "/threads/{conversation_id}",
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
)
async def chat(
    request: ChatRequest,
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

        result = graph.invoke(
            {
                "messages": messages,
                "iteration": 0,
            }
        )

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