import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

# LangChain 1.x uses LangGraph for agents
# create_react_agent builds the think → act → observe loop
# MemorySaver is LangGraph's built-in memory (we use our own instead)
from langgraph.prebuilt import create_react_agent

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class AgentConfigError(RuntimeError):
    pass


def _get_llm():
    provider = os.getenv("AI_PROVIDER", "google").strip().lower()

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY", "")
        model   = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
        if not api_key:
            raise AgentConfigError("GOOGLE_API_KEY is not set.")
        return ChatGoogleGenerativeAI(
            model=model, google_api_key=api_key, temperature=0
        ), provider, model

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        model   = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        if not api_key:
            raise AgentConfigError("ANTHROPIC_API_KEY is not set.")
        return ChatAnthropic(
            model=model, anthropic_api_key=api_key, temperature=0
        ), provider, model

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY", "")
        model   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            raise AgentConfigError("OPENAI_API_KEY is not set.")
        return ChatOpenAI(
            model=model, openai_api_key=api_key, temperature=0
        ), provider, model

    raise AgentConfigError("AI_PROVIDER must be 'google', 'anthropic', or 'openai'.")


async def run_agent(
    message: str,
    session_id: str = "default",
) -> tuple[str, str, str]:

    from .tools import ALL_TOOLS
    from .memory_store import get_memory

    llm, provider, model = _get_llm()

    # create_react_agent from LangGraph replaces AgentExecutor
    # it takes the llm, tools, and an optional system prompt
    # internally it builds the think → call tool → observe loop
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=(
            "You are a smart assistant with access to tools.\n"
            "Use search_docs for questions about our project docs.\n"
            "Use get_weather for weather questions.\n"
            "Use calculator for any math calculation.\n"
            "Think step by step. Use tools when needed.\n"
            "If you already know the answer, reply directly."
        ),
    )

    # get existing chat history for this session
    history = get_memory(session_id)
    history_messages = history.messages  # list of HumanMessage / AIMessage

    # build the full message list:
    # previous history + current user message
    from langchain_core.messages import HumanMessage

    all_messages = history_messages + [HumanMessage(content=message)]

    # invoke the agent with full message history
    result = await agent.ainvoke(
    {"messages": all_messages},
    config={
        # LangSmith metadata for agent traces
        "run_name": "agent-run",
        "tags": ["agent", session_id],
        "metadata": {
            "session_id": session_id,
            "provider":   provider,
            "model":      model,
            "tools":      [t.name for t in ALL_TOOLS],
        },
    },
)

    # LangGraph returns a dict with "messages" list
    # last message is the final AI reply
    reply = result["messages"][-1].content

    # save the new human + ai messages to memory manually
    from langchain_core.messages import AIMessage
    history.add_user_message(message)
    history.add_ai_message(reply)

    return reply, provider, model