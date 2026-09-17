# Reminder Feature Implementation Log

## What was implemented

Persistent SQLite-backed reminders are available through REST APIs and through
the existing LangGraph chat agent. A reminder belongs to one `conversation_id`
and stores its task text, ISO 8601 due time, status, and audit timestamps.

## Files created

- `backend/reminders.py` — reminder SQLite schema and CRUD operations.
- `backend/routes/reminders.py` — documented FastAPI reminder endpoints.
- `docs/reminder_feature.md` — this implementation log.

## Files modified

- `backend/models.py` — reminder request/response schemas.
- `backend/memory.py` — startup initialization and reminder cleanup on thread deletion.
- `backend/tools.py` — five reminder tools and active-chat context binding.
- `backend/agent.py` — tool registration and reminder instructions.
- `backend/routes/chat.py` — binds the current conversation while LangGraph runs.
- `backend/main.py` — registers the reminder router.

## Database schema

`chat_history.db` now contains:

```sql
CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    reminder_text TEXT NOT NULL,
    due_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES threads(id)
);
```

`idx_reminders_conversation_status_due` supports per-conversation/status lookup.
Deleting a chat thread explicitly deletes all reminders associated with that
thread before deleting messages and the thread.

## API endpoints

- `POST /reminders` — create; returns 201.
- `GET /reminders?conversation_id=&status=` — list, with optional filters.
- `GET /reminders/{reminder_id}` — retrieve one.
- `PATCH /reminders/{reminder_id}` — update supplied text, due time, and/or status.
- `DELETE /reminders/{reminder_id}` — delete.
- `POST /reminders/{reminder_id}/complete` — mark completed.

All reminder read/list operations refresh pending reminders whose `due_at` is in
the past to `overdue`. This is query-time status evaluation only; there is no
background scheduler or notification delivery.

## LangGraph tools and chat integration

The graph retains `search_course_material` and adds:

- `create_reminder`
- `get_reminders`
- `update_reminder`
- `delete_reminder`
- `complete_reminder`

`backend.routes.chat.chat()` sets a request-local conversation context around
`graph.invoke()`. Reminder tools use it to create/list records for the active
thread and to prevent update/delete/complete operations on a reminder from a
different thread. Tool schemas do not expose `conversation_id` to the LLM.

For chat-created/rescheduled reminders, tools require ISO 8601 due timestamps.
The system prompt supplies the current server-local timestamp and instructs the
LLM to convert clear relative requests such as “tomorrow at 7 PM”; ambiguous or
missing date/time should be clarified.

## Swagger usage

Run `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` from the
existing `.venv`, then open `http://127.0.0.1:8000/docs`. The reminder router is
tagged `Reminders` and its schemas/status codes are included in `/openapi.json`.

Example create request:

```json
{
  "conversation_id": "test-conversation",
  "reminder_text": "Study RAG",
  "due_at": "2026-09-18T19:00:00"
}
```

Example partial update request:

```json
{
  "reminder_text": "Study LangGraph RAG"
}
```

## Logging

The reminder persistence and router modules use standard-library logging for
creation, retrieval, updates, completion, deletion, missing IDs, and database/
API errors. Logs use reminder and conversation identifiers rather than message
history.

## Testing performed

- Compiled all backend modules with `python -m compileall -q backend`.
- Started FastAPI from the repository `.venv` and verified `/health`, `/docs`,
  and `/openapi.json`.
- Performed create, filtered list, get, patch, complete, delete, and 404 REST
  checks through HTTP.
- Confirmed a created reminder row in `chat_history.db`, restarted FastAPI, and
  retrieved the same reminder after restart.
- Verified overdue-on-query behavior and reminder cleanup after thread deletion.
- Tested normal chat (no tool), reminder creation/list/completion/deletion via
  LangGraph chat tools, and course-material RAG regression.

## Known limitations

- There is no background scheduler, push notification, email notification, or
  recurring-reminder implementation.
- Due times with no timezone offset are interpreted as the server’s local time
  when evaluating overdue state. ISO timestamps with offsets are compared in UTC.
- The LLM performs relative natural-language date conversion; unclear dates or
  times need user clarification. REST clients should send ISO 8601 datetimes.

## Future improvements

- Add authenticated user ownership before exposing reminders across users.
- Add notification delivery and a scheduled overdue processor if product
  requirements need proactive alerts.
- Add recurrence fields and migration support only when recurrence is required.
