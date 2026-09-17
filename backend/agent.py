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
from backend.tools import search_course_material


# ============================================================
# STATE
# ============================================================

class AgentState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]

    iteration: int


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
    search_course_material
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
"""


# ============================================================
# AGENT NODE
# ============================================================

def agent_node(
    state: AgentState,
):

    messages = state["messages"]

    system_message = SystemMessage(
        content=SYSTEM_PROMPT
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

        return "end"

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

    return "end"


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


workflow.set_entry_point(
    "agent"
)


workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "end": END,
    },
)


workflow.add_edge(
    "tools",
    "agent",
)


# ============================================================
# COMPILE
# ============================================================

graph = workflow.compile()