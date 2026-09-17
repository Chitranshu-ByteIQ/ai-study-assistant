# Long-Term Memory

## Overview and architecture

Long-term memory is durable user context, separate from per-thread chat history.
The LangGraph workflow now ends completed turns through `memory_node`. That node
extracts explicit durable facts from the latest user message and stores them in
SQLite. Before the agent runs on a later message, the chat route retrieves only
memories relevant to that message and supplies them as system context.

## User identity and cross-thread behavior

There is no authentication system. Clients provide a stable `X-User-ID` header;
the Streamlit app creates one UUID per browser session. Memory is keyed by this
ID, not by `conversation_id`, so a fact captured in Thread A can answer a
question in Thread B for the same user.

## Extraction, storage, and retrieval

The memory node intentionally saves only explicit patterns for names,
preferences, learning focus, and study goals. It skips ordinary study questions.
`memories` has a unique `(user_id, key)` constraint, so repeated facts update
instead of duplicate. Retrieval uses lightweight keyword matching and injects no
memory when none is relevant; “what do you remember about me?” returns all of a
user's memories as context.

## Database schema

```text
memories(
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  category TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(user_id, key)
)
```

The table and user/category index are created safely at backend startup in the
existing `chat_history.db`. No existing data is reset.

## API reference

All endpoints require `X-User-ID`.

### POST /memory

Creates or updates one manually managed memory.

- Body: `{"key":"name","value":"Chitranshu","category":"profile"}`
- Response: `MemoryResponse`, HTTP 201
- Errors: 400 invalid durable-memory data; 422 validation error; 500 storage error.

### GET /memory

Lists the current user's memories.

- Query: optional `category` (`profile`, `preference`, `learning`, `goal`, `context`)
- Response: `list[MemoryResponse]`, HTTP 200
- Errors: 422 missing/invalid header or filter; 500 storage error.

### DELETE /memory/{memory_id}

Forgets one memory owned by the current user.

- Path parameter: `memory_id`, the persistent memory identifier.
- Response: `{"message":"Memory forgotten","memory_id":"..."}`, HTTP 200
- Errors: 404 missing/not-owned memory; 422 missing header; 500 storage error.

Swagger at `/docs` contains request/response field descriptions, examples,
header/query parameter documentation, and response status descriptions.

## Streamlit UI

The sidebar navigation is ordered Memory, Reminders, Chat. The Memory page calls
`GET /memory`, presents readable cards, and calls `DELETE /memory/{memory_id}`
for Forget. The Reminder page uses reminder APIs; it does not access SQLite.

## Testing and limitations

Backend/API and graph integration are tested with explicit memory creation,
duplicate upsert, retrieval, deletion, and cross-thread chat. The current
extractor is deliberately conservative and pattern-based. There is no user
authentication, semantic memory search, memory editing UI, or background task.
