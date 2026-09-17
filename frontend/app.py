from datetime import datetime
import uuid

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Study Assistant", page_icon="📚", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "page" not in st.session_state:
    st.session_state.page = "💬 Chat"


def headers() -> dict:
    return {"X-User-ID": st.session_state.user_id}


def request_api(method: str, path: str, **kwargs):
    kwargs.setdefault("headers", headers())
    kwargs.setdefault("timeout", 120)
    return requests.request(method, f"{API_URL}{path}", **kwargs)


def get_threads() -> list[dict]:
    response = request_api("GET", "/chat/threads")
    response.raise_for_status()
    return response.json()


def create_thread() -> dict:
    response = request_api("POST", "/chat/threads", json={"title": "New Chat"})
    response.raise_for_status()
    return response.json()


def get_thread(conversation_id: str) -> dict:
    response = request_api("GET", f"/chat/threads/{conversation_id}")
    response.raise_for_status()
    return response.json()


def delete_thread(conversation_id: str) -> None:
    response = request_api("DELETE", f"/chat/threads/{conversation_id}")
    response.raise_for_status()


def send_chat_message(conversation_id: str, message: str) -> dict:
    response = request_api(
        "POST",
        "/chat/",
        json={"conversation_id": conversation_id, "message": message},
    )
    response.raise_for_status()
    return response.json()


def get_memories() -> list[dict]:
    response = request_api("GET", "/memory")
    response.raise_for_status()
    return response.json()


def forget_memory(memory_id: str) -> None:
    response = request_api("DELETE", f"/memory/{memory_id}")
    response.raise_for_status()


def get_reminders(conversation_id: str | None = None) -> list[dict]:
    params = {"conversation_id": conversation_id} if conversation_id else None
    response = request_api("GET", "/reminders", params=params)
    response.raise_for_status()
    return response.json()


def create_reminder(conversation_id: str, text: str, due_at: datetime) -> None:
    response = request_api(
        "POST",
        "/reminders",
        json={"conversation_id": conversation_id, "reminder_text": text, "due_at": due_at.isoformat()},
    )
    response.raise_for_status()


def update_reminder(reminder_id: str, payload: dict) -> None:
    response = request_api("PATCH", f"/reminders/{reminder_id}", json=payload)
    response.raise_for_status()


def complete_reminder(reminder_id: str) -> None:
    response = request_api("POST", f"/reminders/{reminder_id}/complete")
    response.raise_for_status()


def delete_reminder(reminder_id: str) -> None:
    response = request_api("DELETE", f"/reminders/{reminder_id}")
    response.raise_for_status()


def api_error(error: Exception) -> None:
    st.error(f"Backend request failed: {error}")


try:
    threads = get_threads()
except requests.RequestException as error:
    threads = []
    backend_error = error
else:
    backend_error = None

with st.sidebar:
    st.title("📚 AI Study Assistant")
    if st.button("➕ New Chat", use_container_width=True):
        try:
            thread = create_thread()
            st.session_state.current_conversation_id = thread["conversation_id"]
            st.session_state.page = "💬 Chat"
            st.rerun()
        except requests.RequestException as error:
            api_error(error)

    st.divider()
    st.markdown("### Conversations")
    for thread in threads:
        is_active = thread["conversation_id"] == st.session_state.current_conversation_id
        label = f"🟢 {thread['title']}" if is_active else f"💬 {thread['title']}"
        if st.button(label, key=f"thread_{thread['conversation_id']}", use_container_width=True):
            st.session_state.current_conversation_id = thread["conversation_id"]
            st.session_state.page = "💬 Chat"
            st.rerun()

    st.divider()
    st.session_state.page = st.radio(
        "Navigation",
        ["🧠 Memory", "🔔 Reminders", "💬 Chat"],
        index=["🧠 Memory", "🔔 Reminders", "💬 Chat"].index(st.session_state.page),
        label_visibility="collapsed",
    )
    st.caption("Memories are scoped to this browser session's user ID.")

if backend_error:
    st.warning("The backend is unavailable. Start FastAPI at http://127.0.0.1:8000.")


if st.session_state.page == "🧠 Memory":
    st.title("🧠 Long-Term Memory")
    st.caption("Things the assistant has learned about you across conversations.")
    try:
        memories = get_memories()
    except requests.RequestException as error:
        api_error(error)
        memories = []

    if not memories:
        st.info("No long-term memories yet. Tell the assistant your name, preferences, learning focus, or study goals.")
    for memory in memories:
        with st.container(border=True):
            st.markdown(f"#### {memory['key'].replace('_', ' ').title()}")
            st.write(memory["value"])
            st.caption(memory["category"].title())
            if st.button("Forget", key=f"forget_{memory['id']}"):
                try:
                    forget_memory(memory["id"])
                    st.rerun()
                except requests.RequestException as error:
                    api_error(error)


elif st.session_state.page == "🔔 Reminders":
    st.title("🔔 Study Reminders")
    conversation_id = st.session_state.current_conversation_id
    if not conversation_id:
        st.info("Create or select a chat first. Reminders belong to a conversation.")
    else:
        with st.form("create_reminder"):
            reminder_text = st.text_input("What should you study?")
            due_date = st.date_input("Due date")
            due_time = st.time_input("Due time")
            submitted = st.form_submit_button("Create reminder")
        if submitted:
            try:
                create_reminder(conversation_id, reminder_text, datetime.combine(due_date, due_time))
                st.rerun()
            except requests.RequestException as error:
                api_error(error)

        try:
            reminders = get_reminders(conversation_id)
        except requests.RequestException as error:
            api_error(error)
            reminders = []
        if not reminders:
            st.info("No reminders for this conversation.")
        for reminder in reminders:
            with st.container(border=True):
                st.markdown(f"#### {reminder['reminder_text']}")
                st.caption(f"Due: {reminder['due_at']} · Status: {reminder['status'].title()}")
                left, middle, _ = st.columns(3)
                if reminder["status"] not in {"completed", "cancelled"} and left.button("Complete", key=f"complete_{reminder['id']}"):
                    try:
                        complete_reminder(reminder["id"])
                        st.rerun()
                    except requests.RequestException as error:
                        api_error(error)
                if middle.button("Delete", key=f"delete_{reminder['id']}"):
                    try:
                        delete_reminder(reminder["id"])
                        st.rerun()
                    except requests.RequestException as error:
                        api_error(error)
                with st.expander("Edit"):
                    new_text = st.text_input("Reminder", value=reminder["reminder_text"], key=f"text_{reminder['id']}")
                    new_status = st.selectbox("Status", ["pending", "completed", "cancelled"], key=f"status_{reminder['id']}")
                    if st.button("Save changes", key=f"save_{reminder['id']}"):
                        try:
                            update_reminder(reminder["id"], {"reminder_text": new_text, "status": new_status})
                            st.rerun()
                        except requests.RequestException as error:
                            api_error(error)


else:
    st.title("💬 AI Study Assistant")
    st.caption("Ask about your course, study reminders, or what the assistant remembers about you.")
    conversation_id = st.session_state.current_conversation_id
    if not conversation_id:
        st.info("Create a new chat to begin.")
    else:
        try:
            messages = get_thread(conversation_id)["messages"]
        except requests.RequestException as error:
            api_error(error)
            messages = []
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if st.button("Delete this chat", type="secondary"):
            try:
                delete_thread(conversation_id)
                st.session_state.current_conversation_id = None
                st.rerun()
            except requests.RequestException as error:
                api_error(error)

        prompt = st.chat_input("Ask anything about your course...")
        if prompt:
            try:
                with st.spinner("AI is thinking..."):
                    result = send_chat_message(conversation_id, prompt)
                if result.get("tool_used"):
                    st.caption(f"Tool used: {result['tool_used']}")
                if result.get("sources"):
                    with st.expander("Sources"):
                        for source in result["sources"]:
                            st.write(source)
                st.rerun()
            except requests.RequestException as error:
                api_error(error)
