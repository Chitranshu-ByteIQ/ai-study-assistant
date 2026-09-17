from langchain_chroma import Chroma

from langchain_huggingface import (
    HuggingFaceEmbeddings,
)

from backend.config import settings

# ============================================================
# EMBEDDINGS
# ============================================================

embeddings = HuggingFaceEmbeddings(
    model_name=(
        "sentence-transformers/"
        "all-MiniLM-L6-v2"
    )
)


# ============================================================
# EXISTING CHROMA DATABASE
# ============================================================

vector_store = Chroma(
    persist_directory=settings.chroma_path,
    embedding_function=embeddings,
)


# ============================================================
# RETRIEVER
# ============================================================

retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 3
    }
)


