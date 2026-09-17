from langchain_core.tools import tool

from backend.vector_store import retriever


@tool
def search_course_material(query: str) -> str:
    """
    Search the student's course material.

    Use this tool when the student asks about
    course concepts, lectures, notes, RAG,
    embeddings, vector databases, LangChain,
    LangGraph, or other topics that should be
    answered from the student's course material.
    """

    documents = retriever.invoke(query)

    if not documents:

        return (
            "No relevant course material was found."
        )

    results = []

    for document in documents:

        source = document.metadata.get(
            "source",
            "unknown",
        )

        results.append(
            f"""
Source: {source}

Content:
{document.page_content}
"""
        )

    return "\n\n".join(results)

