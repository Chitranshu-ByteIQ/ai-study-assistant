from fastapi import APIRouter, HTTPException

from backend.models import (
    ChatRequest,
    ChatResponse,
)

from backend.agent import graph

from backend.memory import (
    get_history,
    save_message,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post(
    "/",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
):

    try:

        # ----------------------------------------------------
        # Load SQLite conversation
        # ----------------------------------------------------

        history = get_history(
            request.conversation_id
        )


        # ----------------------------------------------------
        # Add current question
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
        # Get final message
        # ----------------------------------------------------

        final_message = (
            result["messages"][-1]
        )

        response = final_message.content


        # ----------------------------------------------------
        # Detect tool usage
        # ----------------------------------------------------

        tool_used = None
        sources = []


        for message in result["messages"]:

            if message.type == "tool":

                tool_used = (
                    message.name
                )


                # Try to extract sources
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
        # Save conversation
        # ----------------------------------------------------

        save_message(
            conversation_id=(
                request.conversation_id
            ),
            role="user",
            content=request.message,
        )


        save_message(
            conversation_id=(
                request.conversation_id
            ),
            role="assistant",
            content=response,
        )


        return ChatResponse(
            response=response,
            conversation_id=(
                request.conversation_id
            ),
            tool_used=tool_used,
            sources=list(
                dict.fromkeys(sources)
            ),
        )


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )