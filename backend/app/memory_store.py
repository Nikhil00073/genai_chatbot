from langchain_community.chat_message_histories import ChatMessageHistory

_sessions: dict[str, ChatMessageHistory] = {}


def get_memory(session_id: str) -> ChatMessageHistory:
    if session_id not in _sessions:
        _sessions[session_id] = ChatMessageHistory()
    return _sessions[session_id]


def clear_memory(session_id: str) -> None:
    if session_id in _sessions:
        del _sessions[session_id]