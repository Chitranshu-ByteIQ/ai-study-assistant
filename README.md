# AI Study Assistant

An AI-powered study companion with course-material RAG, persistent chat threads,
study reminders, and cross-thread long-term memory.

## Features

- Ask course questions with a LangGraph agent and Chroma-backed RAG.
- Keep chat threads and messages in SQLite.
- Create, list, update, complete, and delete reminders through REST or chat.
- Remember durable facts such as a name, learning preference, learning focus, or
  study goal across separate conversations.
- Manage memories and reminders from Streamlit or FastAPI Swagger.

## Architecture

```text
Streamlit UI / API client
            |
          FastAPI
            |
        LangGraph agent
      /        |         \
   RAG     Reminders   Long-term memory
 Chroma      SQLite         SQLite
```

Conversation history is stored per thread in `chat_history.db`. Long-term memory
is separate and global for this single-user application, so a new thread can
use durable context from earlier threads.

## Requirements

- Python environment already provided in `.venv`
- A `GROQ_API_KEY` in `.env`

The course vector store is already persisted at `data/student_content.db`.

## Run the backend

```powershell
cd C:\Users\chitr\Documents\Projects\ai-study-assistant
& .\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

Open the API documentation at <http://127.0.0.1:8000/docs> and the OpenAPI
contract at <http://127.0.0.1:8000/openapi.json>.

## Run the Streamlit app

In a second terminal with the same environment active:

```powershell
streamlit run frontend/app.py
```

The frontend expects FastAPI at `http://127.0.0.1:8000`.

## API overview

| Area | Main endpoints |
|---|---|
| Chat | `POST /chat/threads`, `GET /chat/threads`, `GET/DELETE /chat/threads/{conversation_id}`, `POST /chat/` |
| Reminders | `POST/GET /reminders`, `GET/PATCH/DELETE /reminders/{reminder_id}`, `POST /reminders/{reminder_id}/complete` |
| Memory | `POST/GET /memory`, `DELETE /memory/{memory_id}` |

Example manual memory creation:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/memory `
  -ContentType 'application/json' `
  -Body '{"key":"name","value":"Chitranshu","category":"profile"}'
```

## Long-term memory behavior

The graph's memory node extracts only explicit durable statements, such as:

- `My name is Chitranshu.`
- `I prefer beginner-friendly explanations.`
- `I'm currently learning LangGraph.`
- `I'm preparing for a LangChain interview.`

Memories are upserted by a global `key`, preventing duplicate records. On a
later message, only relevant global memories are injected into the agent prompt.
Users can inspect and forget them via the Memory page or API.

## Limitations

- Memory extraction is focused on explicit durable facts and uses a conservative
  fallback if the structured extractor is unavailable.
- Reminder status becomes overdue when read; no background notification service
  or recurrence engine is included.

## Documentation

- [Reminder feature](docs/reminder_feature.md)
- [Long-term memory](docs/long_term_memory.md)
