import logging

from fastapi import APIRouter, HTTPException, Query, status

from backend.models import (
    ReminderCreateRequest,
    ReminderResponse,
    ReminderStatus,
    ReminderUpdateRequest,
)
from backend.reminders import (
    complete_reminder,
    create_reminder,
    delete_reminder,
    get_reminder,
    get_reminders,
    update_reminder,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reminders", tags=["Reminders"])


def _not_found(reminder_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail="Reminder not found")


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reminder",
)
async def create_reminder_endpoint(request: ReminderCreateRequest):
    try:
        reminder = create_reminder(
            conversation_id=request.conversation_id,
            reminder_text=request.reminder_text,
            due_at=request.due_at.isoformat(),
        )
        logger.info("Reminder API request processed: operation=create")
        return reminder
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        logger.exception("Reminder API create failed")
        raise HTTPException(status_code=500, detail="Unable to create reminder")


@router.get("", response_model=list[ReminderResponse], summary="List reminders")
async def list_reminders(
    conversation_id: str | None = Query(default=None, min_length=1),
    status_filter: ReminderStatus | None = Query(default=None, alias="status"),
):
    try:
        reminders = get_reminders(conversation_id=conversation_id, status=status_filter)
        logger.info("Reminder API request processed: operation=list")
        return reminders
    except Exception:
        logger.exception("Reminder API list failed")
        raise HTTPException(status_code=500, detail="Unable to retrieve reminders")


@router.get(
    "/{reminder_id}", response_model=ReminderResponse, summary="Get one reminder"
)
async def read_reminder(reminder_id: str):
    try:
        reminder = get_reminder(reminder_id)
        if reminder is None:
            raise _not_found(reminder_id)
        logger.info("Reminder API request processed: operation=get reminder_id=%s", reminder_id)
        return reminder
    except HTTPException:
        raise
    except Exception:
        logger.exception("Reminder API get failed: reminder_id=%s", reminder_id)
        raise HTTPException(status_code=500, detail="Unable to retrieve reminder")


@router.patch(
    "/{reminder_id}", response_model=ReminderResponse, summary="Update a reminder"
)
async def patch_reminder(reminder_id: str, request: ReminderUpdateRequest):
    try:
        reminder = update_reminder(
            reminder_id=reminder_id,
            reminder_text=request.reminder_text,
            due_at=request.due_at.isoformat() if request.due_at else None,
            status=request.status,
        )
        if reminder is None:
            raise _not_found(reminder_id)
        logger.info(
            "Reminder API request processed: operation=update reminder_id=%s", reminder_id
        )
        return reminder
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        logger.exception("Reminder API update failed: reminder_id=%s", reminder_id)
        raise HTTPException(status_code=500, detail="Unable to update reminder")


@router.delete("/{reminder_id}", summary="Delete a reminder")
async def remove_reminder(reminder_id: str):
    try:
        if not delete_reminder(reminder_id):
            raise _not_found(reminder_id)
        logger.info(
            "Reminder API request processed: operation=delete reminder_id=%s", reminder_id
        )
        return {"message": "Reminder deleted", "reminder_id": reminder_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Reminder API delete failed: reminder_id=%s", reminder_id)
        raise HTTPException(status_code=500, detail="Unable to delete reminder")


@router.post(
    "/{reminder_id}/complete",
    response_model=ReminderResponse,
    summary="Mark a reminder completed",
)
async def complete_reminder_endpoint(reminder_id: str):
    try:
        reminder = complete_reminder(reminder_id)
        if reminder is None:
            raise _not_found(reminder_id)
        logger.info(
            "Reminder API request processed: operation=complete reminder_id=%s",
            reminder_id,
        )
        return reminder
    except HTTPException:
        raise
    except Exception:
        logger.exception("Reminder API complete failed: reminder_id=%s", reminder_id)
        raise HTTPException(status_code=500, detail="Unable to complete reminder")
