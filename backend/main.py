from fastapi import FastAPI

from backend.routes.chat import router as chat_router
from backend.routes.reminders import router as reminder_router
from backend.routes.memory import router as memory_router


app = FastAPI(
    title="AI Study Assistant",
    description=(
        "AI Study Assistant using "
        "LangChain, LangGraph, FastAPI "
        "and ChromaDB."
    ),
    version="1.0.0",
)


# ============================================================
# ROUTES
# ============================================================

app.include_router(
    chat_router
)

app.include_router(
    reminder_router
)

app.include_router(
    memory_router
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "message": (
            "AI Study Assistant API is running"
        )
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy"
    }
