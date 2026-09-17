# Long-Term Memory

## Overview and architecture

Long-term memory is durable global context, separate from per-thread chat history.
The LangGraph workflow now ends completed turns through `memory_node`. That node
extracts explicit durable facts from the latest user message and stores them in
SQLite. Before the agent runs on a later message, the chat route retrieves only
memories relevant to that message and supplies them as system context.

## Cross-thread behavior

This is a single-user application. Memory is not keyed by `conversation_id` or
an HTTP user identifier, so a fact captured in Thread A can answer a question in
Thread B.

## Extraction, storage, and retrieval

The memory node sends only the latest user message and compact current-memory
context to a focused structured extractor. It ignores ordinary study questions,
upserts changed facts under stable keys, and can remove clearly retracted facts.
The `memories` table has a unique global `key`, so repeated or changed facts are
consolidated instead of duplicated. Retrieval uses lightweight keyword matching;
personal questions and “what do you remember about me?” return global memories.

## Database schema

```text
memories(
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  value TEXT NOT NULL,
  category TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

The table and category index are created safely at backend startup in the
existing `chat_history.db`. Legacy user-scoped rows are migrated to one global
row per key, keeping the most recently updated value.

## API reference

### POST /memory

Creates or updates one global durable memory.

- Body: `{"key":"name","value":"Chitranshu","category":"profile"}`
- Response: `MemoryResponse`, HTTP 201
- Errors: 400 invalid durable-memory data; 422 validation error; 500 storage error.

### GET /memory

Lists all global memories.

- Query: optional `category` (`profile`, `preference`, `learning`, `goal`, `context`)
- Response: `list[MemoryResponse]`, HTTP 200
- Errors: 422 invalid filter; 500 storage error.

### DELETE /memory/{memory_id}

Forgets one global memory.

- Path parameter: `memory_id`, the persistent memory identifier.
- Response: `{"message":"Memory forgotten","memory_id":"..."}`, HTTP 200
- Errors: 404 missing memory; 500 storage error.

Swagger at `/docs` contains request/response field descriptions, examples,
query parameter documentation, and response status descriptions.

## Streamlit UI

The sidebar navigation is ordered Memory, Reminders, Chat. The Memory page calls
`GET /memory`, presents readable cards, and calls `DELETE /memory/{memory_id}`
for Forget. The Reminder page uses reminder APIs; it does not access SQLite.

## Testing and limitations

Backend/API and graph integration are tested with explicit memory creation,
duplicate upsert, retrieval, deletion, and cross-thread chat. The extractor is
focused and structured, with a conservative fallback. There is no semantic
memory search, memory editing UI, or background task.
