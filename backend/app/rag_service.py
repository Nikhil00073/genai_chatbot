import os
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

# Path to the folder where your .txt documents live
DOCS_PATH = Path(__file__).resolve().parent / "docs"

# Path where ChromaDB will save the vector database on disk
# So you do not have to re-embed documents every time the server starts
CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"


# ── Step 1: Load documents from the docs/ folder ─────────────
# DirectoryLoader reads every .txt file in the folder
# TextLoader handles the actual file reading
def _load_documents():
    loader = DirectoryLoader(
        str(DOCS_PATH),
        glob="**/*.txt",        # match all .txt files recursively
        loader_cls=TextLoader,  # use TextLoader for each file
        show_progress=True,
    )
    docs = loader.load()
    print(f"[RAG] Loaded {len(docs)} document(s)")
    return docs


# ── Step 2: Split documents into small chunks ─────────────────
# LLMs have a context limit — you can not send an entire document
# So we split documents into small overlapping chunks
# chunk_size = how many characters per chunk
# chunk_overlap = how many characters repeat between chunks
#                 overlap helps preserve context at chunk boundaries
def _split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # each chunk is max 500 characters
        chunk_overlap=50,    # 50 characters shared between consecutive chunks
    )
    chunks = splitter.split_documents(docs)
    print(f"[RAG] Split into {len(chunks)} chunk(s)")
    return chunks


# ── Step 3: Create embeddings ─────────────────────────────────
# Embeddings convert text into a list of numbers (a vector)
# Similar meaning = similar numbers = close in vector space
# "FastAPI is a framework" and "FastAPI builds APIs" will be close
# We use SentenceTransformer — free, runs locally, no API key needed
def _get_embeddings():
    return SentenceTransformerEmbeddings(
        model_name="all-MiniLM-L6-v2"  # small, fast, good quality model
    )


# ── Step 4: Build or load the vector store ───────────────────
# ChromaDB is a local vector database — stores all embedded chunks on disk
# If the database already exists — load it (fast)
# If it does not exist — create it by embedding all chunks (slow, one time)
def _get_vector_store():
    embeddings = _get_embeddings()

    if CHROMA_PATH.exists():
        # database already built — just load it
        print("[RAG] Loading existing vector store")
        return Chroma(
            persist_directory=str(CHROMA_PATH),
            embedding_function=embeddings,
        )
    else:
        # first time — load docs, split, embed, save to disk
        print("[RAG] Building vector store for the first time")
        docs   = _load_documents()
        chunks = _split_documents(docs)
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=str(CHROMA_PATH),
        )
        return db


# ── Step 5: Build the RAG retriever ──────────────────────────
# A retriever takes a question and returns the most relevant chunks
# search_type="similarity" = find chunks with similar meaning
# k=3 = return top 3 most relevant chunks
def get_retriever():
    db = _get_vector_store()
    return db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )


# ── Step 6: Format retrieved chunks into readable text ───────
# The retriever returns a list of Document objects
# We join them into one string to pass to the LLM
def _format_docs(docs) -> str:
    # Each doc has a .page_content field with the actual text
    return "\n\n".join(doc.page_content for doc in docs)


# ── Step 7: Build the RAG prompt ─────────────────────────────
# Notice we now have a {context} variable — this is where
# the retrieved document chunks get inserted
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


# ── Step 8: Build the full RAG chain ─────────────────────────
# This is the key part — using RunnablePassthrough and RunnableLambda
# together to build the RAG pipeline
#
# Flow:
#   input dict
#     → RunnableParallel runs two things at the same time:
#         context  = retriever finds relevant docs → format to string
#         input    = RunnablePassthrough keeps the original question
#         history  = RunnablePassthrough keeps the chat history
#     → prompt fills in {context}, {history}, {input}
#     → llm generates an answer
#     → parser converts to plain string
def build_rag_chain(llm):
    from langchain_core.runnables import RunnableParallel

    retriever = get_retriever()

    # RunnableParallel runs all three at the same time:
    # context  → call retriever with the input, then format the docs
    # input    → pass the user's question unchanged to the prompt
    # history  → pass the chat history unchanged to the prompt
    setup = RunnableParallel(
        context = RunnableLambda(
            lambda x: _format_docs(retriever.invoke(x["input"]))
        ),
        input   = RunnablePassthrough() | RunnableLambda(lambda x: x["input"]),
        history = RunnablePassthrough() | RunnableLambda(lambda x: x.get("history", [])),
    )

    prompt = build_rag_prompt()
    parser = StrOutputParser()

    # Full RAG chain
    # setup builds context + passes input + history
    # then prompt fills the template
    # then llm answers
    # then parser gives plain string
    chain = setup | prompt | llm | parser
    return chain