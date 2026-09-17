from fastapi import FastAPI

from backend.routes.chat import router as chat_router


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