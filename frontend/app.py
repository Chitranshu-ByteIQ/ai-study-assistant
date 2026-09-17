import uuid

import requests

import streamlit as st


# ============================================================
# CONFIG
# ============================================================

API_URL = (
    "http://127.0.0.1:8000/chat/"
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide",
)


# ============================================================
# SESSION ID
# ============================================================

if "conversation_id" not in st.session_state:

    st.session_state.conversation_id = str(
        uuid.uuid4()
    )


# ============================================================
# CHAT HISTORY
# ============================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("📚 AI Study Assistant")

    st.divider()

    st.markdown(
        "### Navigation"
    )

    page = st.radio(
        "",
        [
            "💬 Chat",
            "📖 Course Material",
            "⏰ Reminders",
            "🧠 Memory",
        ],
    )

    st.divider()

    st.markdown(
        "### Session"
    )

    st.caption(
        st.session_state.conversation_id
    )


# ============================================================
# CHAT PAGE
# ============================================================

if page == "💬 Chat":

    st.title(
        "AI Study Assistant"
    )

    st.caption(
        "Your personal course & study assistant"
    )


    # --------------------------------------------------------
    # Display previous messages
    # --------------------------------------------------------

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )


    # --------------------------------------------------------
    # Chat input
    # --------------------------------------------------------

    user_input = st.chat_input(
        "Ask anything about your course..."
    )


    if user_input:

        # ----------------------------------------------------
        # Display user message
        # ----------------------------------------------------

        st.session_state.messages.append(
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
        # Call FastAPI
        # ----------------------------------------------------

        try:

            with st.spinner(
                "AI is thinking..."
            ):

                response = requests.post(
                    API_URL,
                    json={
                        "message": user_input,
                        "conversation_id": (
                            st.session_state
                            .conversation_id
                        ),
                    },
                    timeout=120,
                )


            if response.status_code != 200:

                st.error(
                    response.text
                )

            else:

                data = response.json()

                answer = data[
                    "response"
                ]

                tool_used = data.get(
                    "tool_used"
                )

                sources = data.get(
                    "sources",
                    [],
                )


                # ------------------------------------------------
                # Display assistant
                # ------------------------------------------------

                with st.chat_message(
                    "assistant"
                ):

                    # Agent action
                    if tool_used:

                        st.info(
                            f"🔧 Tool used: "
                            f"{tool_used}"
                        )


                    st.markdown(
                        answer
                    )


                    # Sources
                    if sources:

                        st.markdown(
                            "### 📚 Sources"
                        )

                        for source in sources:

                            st.caption(
                                f"• {source}"
                            )


                # ------------------------------------------------
                # Save to frontend history
                # ------------------------------------------------

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )


        except requests.exceptions.RequestException:

            st.error(
                "Could not connect to FastAPI. "
                "Make sure the backend is running."
            )


# ============================================================
# COURSE MATERIAL PAGE
# ============================================================

elif page == "📖 Course Material":

    st.title(
        "📖 Course Material"
    )

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
               LLM
        ```
        """
    )


# ============================================================
# REMINDERS PAGE
# ============================================================

elif page == "⏰ Reminders":

    st.title(
        "⏰ Study Reminders"
    )

    st.info(
        "Reminder functionality can be connected "
        "to the same agent using a create_reminder "
        "LangChain tool."
    )


# ============================================================
# MEMORY PAGE
# ============================================================

elif page == "🧠 Memory":

    st.title(
        "🧠 Conversation Memory"
    )

    st.info(
        "Conversation history is persisted in SQLite."
    )

    st.markdown(
        "### Current Conversation"
    )

    for message in st.session_state.messages:

        role = message["role"]

        content = message["content"]

        if role == "user":

            st.markdown(
                f"**You:** {content}"
            )

        else:

            st.markdown(
                f"**AI:** {content}"
            )