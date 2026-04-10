import os
from pathlib import Path
from dotenv import load_dotenv

# load env before anything else so LangSmith picks up the vars
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .chat_service import ChatConfigError, generate_reply
from .agent_service import AgentConfigError, run_agent
from .memory_store import clear_memory


app = FastAPI(title="Chat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message:    str  = Field(..., min_length=1, max_length=4000)
    session_id: str  = Field(default="default")
    use_rag:    bool = Field(default=False)


class AgentRequest(BaseModel):
    message:    str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default")


class ChatResponse(BaseModel):
    reply:    str
    provider: str
    model:    str


# ── health + langsmith status ────────────────────────────────
@app.get("/health")
async def health() -> dict:
    # show LangSmith status so you know if tracing is active
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    project         = os.getenv("LANGCHAIN_PROJECT", "not set")
    return {
        "status":           "ok",
        "langsmith_tracing": tracing_enabled,
        "langsmith_project": project,
    }


# ── chat endpoint ────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        reply, provider, model = await generate_reply(
            payload.message,
            payload.session_id,
            payload.use_rag,
        )
    except ChatConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream API request failed: {exc}"
        ) from exc
    return ChatResponse(reply=reply, provider=provider, model=model)


# ── agent endpoint ───────────────────────────────────────────
@app.post("/agent", response_model=ChatResponse)
async def agent(payload: AgentRequest) -> ChatResponse:
    try:
        reply, provider, model = await run_agent(
            payload.message,
            payload.session_id,
        )
    except AgentConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Agent request failed: {exc}"
        ) from exc
    return ChatResponse(reply=reply, provider=provider, model=model)


# ── clear session ────────────────────────────────────────────
@app.delete("/session/{session_id}")
async def delete_session(session_id: str) -> dict:
    clear_memory(session_id)
    return {"status": "cleared", "session_id": session_id}