from datetime import datetime
from typing import Annotated, TypedDict

from langchain_groq import ChatGroq

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
)

from langgraph.graph import (
    StateGraph,
    END,
)

from langgraph.graph.message import (
    add_messages,
)

from langgraph.prebuilt import ToolNode

from backend.config import settings
from backend.long_term_memory import store_extracted_memories
from backend.tools import (
    complete_reminder,
    create_reminder,
    delete_reminder,
    get_reminders,
    search_course_material,
    update_reminder,
)


# ============================================================
# STATE
# ============================================================

class AgentState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]

    iteration: int

    user_id: str | None

    memory_context: str


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    model=settings.groq_model,
    api_key=settings.groq_api_key,
    temperature=0,
)


# ============================================================
# TOOLS
# ============================================================

tools = [
    search_course_material,
    create_reminder,
    get_reminders,
    update_reminder,
    delete_reminder,
    complete_reminder,
]


llm_with_tools = llm.bind_tools(tools)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an AI Study Assistant.

You help students understand their course material.

You have access to this tool:

search_course_material(query)

You also have reminder tools for the active conversation:

- create_reminder(reminder_text, due_at)
- get_reminders(status)
- update_reminder(reminder_id, reminder_text, due_at, status)
- delete_reminder(reminder_id)
- complete_reminder(reminder_id)

--------------------------------------------------
WHEN TO USE THE TOOL
--------------------------------------------------

Use search_course_material when the student asks
about information that should come from their
course material.

Examples:

- What is RAG?
- Explain embeddings.
- What is a vector database?
- What does the course say about LangChain?
- Explain the RAG architecture from my notes.

--------------------------------------------------
WHEN NOT TO USE THE TOOL
--------------------------------------------------

For normal conversation, do not use the tool.

Examples:

- Hello
- How are you?
- Tell me a joke.

For questions about previous conversation messages,
use the conversation history.

Example:

User:
What is RAG?

User:
What did I just ask?

The second question should be answered from
conversation history.

--------------------------------------------------
RAG ANSWERS
--------------------------------------------------

When course material is retrieved, answer using
the retrieved material.

Do not invent facts that are not present in
the retrieved course material.

If the course material does not contain the answer,
say:

"I don't know based on the provided course material."

Be clear and beginner friendly.

--------------------------------------------------
REMINDERS
--------------------------------------------------

Use reminder tools for requests to create, list, change, complete, or delete
study reminders. Do not use search_course_material for reminder operations.

For create or reschedule operations, pass a complete ISO 8601 datetime to the
tool. The current server-local timestamp is supplied in the system message.
Convert clear relative dates such as "tomorrow at 7 PM" using that timestamp.
If the user did not provide enough date/time information, ask a clarification
question instead of creating a reminder. There is no notification scheduler:
reminders are records that become overdue when queried after their due time.

When a user refers to a reminder without its ID, first call get_reminders to
identify the reminder, then use its returned ID with the requested tool.

--------------------------------------------------
LONG-TERM MEMORY
--------------------------------------------------

Relevant long-term memory, when available, is included in the system context.
Use it to answer questions about the user across separate conversations. Treat
it as user-provided context, not course material. Do not claim to remember a
fact that is absent from the supplied memory context.
"""


# ============================================================
# AGENT NODE
# ============================================================

def agent_node(
    state: AgentState,
):

    messages = state["messages"]

    current_time = datetime.now().astimezone().replace(microsecond=0).isoformat()
    memory_context = state.get("memory_context", "")
    system_message = SystemMessage(
        content=(
            f"{SYSTEM_PROMPT}\n\nCurrent server-local timestamp: {current_time}"
            f"\n\n{memory_context}"
        )
    )

    response = llm_with_tools.invoke(
        [
            system_message,
            *messages,
        ]
    )

    return {
        "messages": [response],
        "iteration": state.get(
            "iteration",
            0,
        ) + 1,
    }


# ============================================================
# TOOL NODE
# ============================================================

tool_node = ToolNode(tools)


# ============================================================
# LONG-TERM MEMORY NODE
# ============================================================

def memory_node(state: AgentState):
    """Persist explicit durable facts after a completed agent turn."""
    user_id = state.get("user_id")

    if not user_id:
        return {}

    user_messages = [
        message
        for message in state["messages"]
        if getattr(message, "type", None) == "human"
    ]

    if user_messages:
        store_extracted_memories(user_id, str(user_messages[-1].content))

    return {}


# ============================================================
# ROUTER
# ============================================================

def should_continue(
    state: AgentState,
):

    messages = state["messages"]

    last_message = messages[-1]

    # --------------------------------------------------------
    # Maximum 3 agent iterations
    # --------------------------------------------------------

    if state.get("iteration", 0) >= 3:

        return "memory"

    # --------------------------------------------------------
    # If LLM requested a tool
    # --------------------------------------------------------

    if getattr(
        last_message,
        "tool_calls",
        None,
    ):

        return "tools"

    # --------------------------------------------------------
    # Otherwise final answer
    # --------------------------------------------------------

    return "memory"


# ============================================================
# LANGGRAPH
# ============================================================

workflow = StateGraph(
    AgentState
)


workflow.add_node(
    "agent",
    agent_node,
)


workflow.add_node(
    "tools",
    tool_node,
)

workflow.add_node(
    "memory",
    memory_node,
)


workflow.set_entry_point(
    "agent"
)


workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "memory": "memory",
    },
)


workflow.add_edge(
    "tools",
    "agent",
)

workflow.add_edge(
    "memory",
    END,
)


# ============================================================
# COMPILE
# ============================================================

graph = workflow.compile()
