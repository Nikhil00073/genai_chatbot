# WAY 1 — using @tool decorator (simplest, most common)
# The function name becomes the tool name
# The docstring is what the agent reads to decide when to use it
# Write a clear docstring — the agent uses it to pick the right tool

from langchain_core.tools import tool
from backend.app.rag_service import get_retriever


@tool
def search_docs(query: str) -> str:
    """
    Search our internal documents and knowledge base.
    Use this tool when the user asks about our API, project,
    FastAPI setup, React app, or LangChain code.
    Returns relevant text from our docs folder.
    """
    # get the retriever from rag_service
    retriever = get_retriever()

    # invoke with the query string — returns list of Document objects
    docs = retriever.invoke(query)

    if not docs:
        return "No relevant documents found for this query."

    # format each document with its source file name
    results = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        results.append(f"[Doc {i} from {source}]:\n{doc.page_content}")

    return "\n\n".join(results)