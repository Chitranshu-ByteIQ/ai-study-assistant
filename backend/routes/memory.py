import logging

from fastapi import APIRouter, HTTPException, Query, status

from backend.long_term_memory import delete_memory, get_memories, upsert_memory
from backend.models import (
    MemoryCategory,
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["Long-Term Memory"])
@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a long-term memory",
    description="Stores one durable fact globally. Reusing a key updates that memory instead of creating a duplicate.",
    responses={400: {"description": "Invalid memory data"}},
)
async def create_memory(request: MemoryCreateRequest):
    try:
        return upsert_memory(request.key, request.value, request.category)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        logger.exception("Memory API create failed")
        raise HTTPException(status_code=500, detail="Unable to store memory")


@router.get(
    "",
    response_model=list[MemoryResponse],
    summary="List long-term memories",
    description="Returns all durable memories shared across chat threads.",
)
async def list_memory(
    category: MemoryCategory | None = Query(default=None, description="Optional memory category filter."),
):
    try:
        return get_memories(category)
    except Exception:
        logger.exception("Memory API list failed")
        raise HTTPException(status_code=500, detail="Unable to retrieve memories")


@router.delete(
    "/{memory_id}",
    response_model=MemoryDeleteResponse,
    summary="Forget one long-term memory",
    description="Permanently removes one global memory.",
    responses={404: {"description": "Memory not found"}},
)
async def remove_memory(
    memory_id: str,
):
    try:
        if not delete_memory(memory_id):
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"message": "Memory forgotten", "memory_id": memory_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Memory API delete failed: memory_id=%s", memory_id)
        raise HTTPException(status_code=500, detail="Unable to forget memory")
