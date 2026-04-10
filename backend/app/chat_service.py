import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableBranch
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class ChatConfigError(RuntimeError):
    pass


def _get_llm():
    provider = os.getenv("AI_PROVIDER", "google").strip().lower()

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY", "")
        model   = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
        if not api_key:
            raise ChatConfigError("GOOGLE_API_KEY is not set.")
        return ChatGoogleGenerativeAI(
            model=model, google_api_key=api_key, temperature=0.7
        ), provider, model

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        model   = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        if not api_key:
            raise ChatConfigError("ANTHROPIC_API_KEY is not set.")
        return ChatAnthropic(
            model=model, anthropic_api_key=api_key, temperature=0.7
        ), provider, model

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY", "")
        model   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            raise ChatConfigError("OPENAI_API_KEY is not set.")
        return ChatOpenAI(
            model=model, openai_api_key=api_key, temperature=0.7
        ), provider, model

    raise ChatConfigError("AI_PROVIDER must be 'google', 'anthropic', or 'openai'.")


# Normal chat prompt — no documents
def _build_general_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful assistant. Be concise and friendly."
        ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])


# ── main function ─────────────────────────────────────────────
async def generate_reply(
    message: str,
    session_id: str = "default",
    use_rag: bool = False,       # ← new flag: True = search docs first
) -> tuple[str, str, str]:

    llm, provider, model = _get_llm()
    parser = StrOutputParser()

    if use_rag:
        # RAG mode — search documents then answer
        from .rag_service import build_rag_chain
        chain = build_rag_chain(llm)
    else:
        # Normal mode — answer from LLM knowledge only
        chain = _build_general_prompt() | llm | parser

    from .memory_store import get_memory

    chain_with_memory = RunnableWithMessageHistory(
        chain,
        get_memory,
        input_messages_key="input",
        history_messages_key="history",
    )

    reply = await chain_with_memory.ainvoke(
    {"input": message},
    config={
        "configurable": {"session_id": session_id},
        # LangSmith metadata — shows up in dashboard per trace
        "run_name": f"chat-{'rag' if use_rag else 'normal'}",
        "tags": ["chat", "rag" if use_rag else "normal", session_id],
        "metadata": {
            "session_id": session_id,
            "mode":       "rag" if use_rag else "chat",
            "provider":   provider,
            "model":      model,
        },
    },
)

    return reply, provider, model