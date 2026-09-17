import uuid

import requests
import streamlit as st


# ============================================================
# CONFIG
# ============================================================

API_URL = "http://127.0.0.1:8000"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide",
)


# ============================================================
# SESSION STATE
# ============================================================

# All chat threads known to the frontend
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = {}


# Current active conversation
if "current_conversation_id" not in st.session_state:
    conversation_id = str(uuid.uuid4())

    st.session_state.current_conversation_id = conversation_id

    st.session_state.chat_threads[conversation_id] = {
        "title": "New Chat",
    }


# Current page
if "page" not in st.session_state:
    st.session_state.page = "💬 Chat"


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def create_new_chat():
    """
    Create a new conversation/thread.
    """

    conversation_id = str(uuid.uuid4())

    st.session_state.chat_threads[conversation_id] = {
        "title": "New Chat",
    }

    st.session_state.current_conversation_id = conversation_id


def get_current_conversation_id():
    """
    Return the active LangGraph thread ID.
    """

    return st.session_state.current_conversation_id


def send_message(message: str):
    """
    Send the user's message to FastAPI.
    """

    conversation_id = get_current_conversation_id()

    response = requests.post(
        f"{API_URL}/chat/",
        json={
            "message": message,
            "conversation_id": conversation_id,
        },
        timeout=120,
    )

    return response


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("📚 AI Study Assistant")

    st.divider()

    # --------------------------------------------------------
    # NEW CHAT
    # --------------------------------------------------------

    if st.button(
        "➕ New Chat",
        use_container_width=True,
    ):

        create_new_chat()

        st.rerun()

    st.divider()

    # --------------------------------------------------------
    # CHAT THREADS
    # --------------------------------------------------------

    st.markdown("### 💬 Conversations")

    if st.session_state.chat_threads:

        for conversation_id, chat in list(
            st.session_state.chat_threads.items()
        ):

            title = chat.get(
                "title",
                "New Chat",
            )

            is_current = (
                conversation_id
                == st.session_state.current_conversation_id
            )

            button_label = (
                f"🟢 {title}"
                if is_current
                else f"💬 {title}"
            )

            if st.button(
                button_label,
                key=f"chat_{conversation_id}",
                use_container_width=True,
            ):

                st.session_state.current_conversation_id = (
                    conversation_id
                )

                st.session_state.page = "💬 Chat"

                st.rerun()

    st.divider()

    # --------------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------------

    st.markdown("### Navigation")

    page = st.radio(
        "Navigation",
        [
            "💬 Chat",
            "📖 Course Material",
            "⏰ Reminders",
            "🧠 Memory",
        ],
        label_visibility="collapsed",
    )

    st.session_state.page = page

    st.divider()

    # --------------------------------------------------------
    # CURRENT THREAD
    # --------------------------------------------------------

    st.markdown("### Current Thread")

    st.caption(
        st.session_state.current_conversation_id
    )


# ============================================================
# CHAT PAGE
# ============================================================

if st.session_state.page == "💬 Chat":

    st.title("AI Study Assistant")

    st.caption(
        "Your personal course & study assistant"
    )

    conversation_id = (
        st.session_state.current_conversation_id
    )

    # --------------------------------------------------------
    # Load messages for current thread
    # --------------------------------------------------------
    #
    # IMPORTANT:
    #
    # We don't use our own SQLite chat history anymore.
    #
    # LangGraph owns the conversation state.
    #
    # The frontend can request the thread history
    # from the backend if that endpoint exists.
    #
    # For now, we maintain the displayed messages
    # temporarily in Streamlit session state.
    #
    # --------------------------------------------------------

    thread = st.session_state.chat_threads[
        conversation_id
    ]

    if "messages" not in thread:

        thread["messages"] = []


    # --------------------------------------------------------
    # Display conversation
    # --------------------------------------------------------

    for message in thread["messages"]:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

            # Display tool information
            if message.get("tool_used"):

                st.caption(
                    f"🔧 Tool: "
                    f"{message['tool_used']}"
                )

            # Display sources
            if message.get("sources"):

                with st.expander(
                    "📚 Sources"
                ):

                    for source in message[
                        "sources"
                    ]:

                        st.caption(
                            f"• {source}"
                        )


    # --------------------------------------------------------
    # Chat input
    # --------------------------------------------------------

    user_input = st.chat_input(
        "Ask anything about your course..."
    )


    if user_input:

        # ----------------------------------------------------
        # Update chat title
        # ----------------------------------------------------

        if thread["title"] == "New Chat":

            title = user_input[:40]

            if len(user_input) > 40:

                title += "..."

            thread["title"] = title


        # ----------------------------------------------------
        # Display user message
        # ----------------------------------------------------

        thread["messages"].append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        with st.chat_message("user"):

            st.markdown(
                user_input
            )


        # ----------------------------------------------------
        # Call backend
        # ----------------------------------------------------

        try:

            with st.spinner(
                "AI is thinking..."
            ):

                response = send_message(
                    user_input
                )


            # ------------------------------------------------
            # Backend error
            # ------------------------------------------------

            if response.status_code != 200:

                st.error(
                    f"Backend error: "
                    f"{response.text}"
                )

            else:

                data = response.json()

                answer = data.get(
                    "response",
                    "No response received.",
                )

                tool_used = data.get(
                    "tool_used"
                )

                sources = data.get(
                    "sources",
                    [],
                )


                # ------------------------------------------------
                # Save assistant message
                # ------------------------------------------------

                thread["messages"].append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "tool_used": tool_used,
                        "sources": sources,
                    }
                )


                # ------------------------------------------------
                # Display assistant
                # ------------------------------------------------

                with st.chat_message(
                    "assistant"
                ):

                    if tool_used:

                        st.info(
                            f"🔧 Tool used: "
                            f"{tool_used}"
                        )

                    st.markdown(
                        answer
                    )


                    # --------------------------------------------
                    # Sources
                    # --------------------------------------------

                    if sources:

                        with st.expander(
                            "📚 Sources"
                        ):

                            for source in sources:

                                st.caption(
                                    f"• {source}"
                                )


        except requests.exceptions.ConnectionError:

            st.error(
                "❌ Could not connect to FastAPI.\n\n"
                "Make sure the backend is running on "
                "http://127.0.0.1:8000"
            )


        except requests.exceptions.Timeout:

            st.error(
                "⏳ The request took too long. "
                "Please try again."
            )


        except requests.exceptions.RequestException as e:

            st.error(
                f"❌ Request failed: {e}"
            )


# ============================================================
# COURSE MATERIAL PAGE
# ============================================================

elif st.session_state.page == "📖 Course Material":

    st.title("📖 Course Material")

    st.info(
        "Course material is stored in the "
        "persistent Chroma vector database."
    )

    st.markdown(
        """
        ### RAG Pipeline

        ```text
        Course .txt files
                ↓
             Chunking
                ↓
            Embeddings
                ↓
             ChromaDB
                ↓
        Semantic Retrieval
                ↓
          Search Tool
                ↓
          LangGraph Agent
                ↓
               LLM
                ↓
             Answer
        ```
        """
    )

    st.markdown(
        "### How the Agent Uses Course Material"
    )

    st.write(
        """
        When you ask a course-related question,
        the LangGraph agent can call the
        `search_course_material` tool.

        The tool performs semantic search against
        the existing ChromaDB and returns relevant
        course material to the LLM.
        """
    )


# ============================================================
# REMINDERS PAGE
# ============================================================

elif st.session_state.page == "⏰ Reminders":

    st.title("⏰ Study Reminders")

    st.write(
        """
        You can create study reminders directly
        through the AI assistant.
        """
    )

    st.markdown(
        "### Example"
    )

    st.code(
        "Remind me to revise RAG tomorrow."
    )

    st.info(
        """
        The LangGraph agent decides whether the
        `create_reminder` tool should be called.

        Example flow:

        User
        ↓
        LangGraph Agent
        ↓
        create_reminder()
        ↓
        Reminder saved
        ↓
        Agent response
        """
    )

    st.markdown(
        "### Ask the Assistant"
    )

    st.write(
        """
        Try asking:

        • "Remind me to study embeddings tomorrow."

        • "Remind me to revise LangGraph on Friday."

        • "Show me my reminders."
        """
    )


# ============================================================
# MEMORY PAGE
# ============================================================

elif st.session_state.page == "🧠 Memory":

    st.title("🧠 Long-Term Memory")

    st.write(
        """
        The assistant can maintain important
        information across conversations.
        """
    )

    st.markdown(
        "### What is stored?"
    )

    st.write(
        """
        The long-term memory system is intended
        for important information such as:

        • Study goals

        • Learning preferences

        • Important facts shared by the student

        • Long-term study context
        """
    )

    st.markdown(
        "### Example"
    )

    st.code(
        """
User:
I am preparing for my LangChain interview.
I prefer beginner-friendly explanations.

↓

Memory Tool

↓

Long-Term Memory:
- Preparing for LangChain interview
- Prefers beginner-friendly explanations
        """
    )

    st.info(
        """
        Conversation persistence and long-term
        memory are two different things.

        LangGraph persistence:
        → preserves conversation/thread state.

        Long-term memory:
        → preserves important information
          across conversations.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "AI Study Assistant • LangChain + LangGraph + FastAPI"
)