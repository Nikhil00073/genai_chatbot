import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DOCS_PATH   = Path(__file__).resolve().parent / "docs"
CHROMA_PATH = Path("/tmp/chroma_db")   # always /tmp — no dimension mismatch


# ── Step 1: embeddings using Google API ──────────────────────
# uses Google's API — zero local RAM, no heavy model to load
# this is the key fix for Render free tier (512MB limit)
def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",  # correct model name for 2025
        google_api_key=api_key,
    )


# ── Step 2: load documents ────────────────────────────────────
def _load_documents():
    if not DOCS_PATH.exists():
        DOCS_PATH.mkdir(parents=True, exist_ok=True)
        print(f"[RAG] Created docs folder at {DOCS_PATH}")
        return []

    loader = DirectoryLoader(
        str(DOCS_PATH),
        glob="**/*.txt",
        loader_cls=TextLoader,
        show_progress=False,  # disable progress bar on server
    )
    docs = loader.load()
    print(f"[RAG] Loaded {len(docs)} document(s)")
    return docs


# ── Step 3: split into chunks ─────────────────────────────────
def _split_documents(docs):
    if not docs:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(docs)
    print(f"[RAG] Split into {len(chunks)} chunk(s)")
    return chunks


# ── Step 4: build or load vector store ───────────────────────
def _get_vector_store():
    embeddings = _get_embeddings()

    # always clear and rebuild — ensures no dimension mismatch
    # from old sentence-transformers DB (384 dim) vs Google (3072 dim)
    if CHROMA_PATH.exists():
        shutil.rmtree(CHROMA_PATH)
        print("[RAG] Cleared old vector store — rebuilding fresh")

    docs   = _load_documents()
    chunks = _split_documents(docs)

    if not chunks:
        print("[RAG] No documents found — creating empty store")
        return Chroma(
            persist_directory=str(CHROMA_PATH),
            embedding_function=embeddings,
        )

    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH),
    )
    print("[RAG] Vector store built successfully")
    return db


# ── Step 5: retriever ─────────────────────────────────────────
def get_retriever():
    db = _get_vector_store()
    return db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )


# ── Step 6: format retrieved docs ────────────────────────────
def _format_docs(docs) -> str:
    if not docs:
        return "No relevant documents found."
    return "\n\n".join(doc.page_content for doc in docs)


# ── Step 7: RAG prompt ────────────────────────────────────────
def build_rag_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful assistant. "
            "Use the following context from our documents to answer the question. "
            "If the answer is not in the context, say you don't know — do not make up answers.\n\n"
            "Context:\n{context}"
        ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])


# ── Step 8: full RAG chain ────────────────────────────────────
def build_rag_chain(llm):
    retriever = get_retriever()

    setup = RunnableParallel(
        context=RunnableLambda(
            lambda x: _format_docs(retriever.invoke(x["input"]))
        ),
        input=RunnablePassthrough() | RunnableLambda(lambda x: x["input"]),
        history=RunnablePassthrough() | RunnableLambda(lambda x: x.get("history", [])),
    )

    prompt = build_rag_prompt()
    parser = StrOutputParser()

    chain = setup | prompt | llm | parser
    return chain