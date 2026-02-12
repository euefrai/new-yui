"""
Contexto da execução atual do agente (user_id, chat_id).
Permite que tools como create_mission usem o contexto da sessão.
"""
from contextvars import ContextVar

_current_user_id: ContextVar[str] = ContextVar("agent_user_id", default="")
_current_chat_id: ContextVar[str] = ContextVar("agent_chat_id", default="")


def set_agent_context(user_id: str = "", chat_id: str = "") -> None:
    """Define o contexto da sessão atual para as tools."""
    _current_user_id.set(user_id or "")
    _current_chat_id.set(chat_id or "")


def get_agent_context() -> tuple:
    """Retorna (user_id, chat_id) do contexto atual."""
    return (_current_user_id.get(), _current_chat_id.get())
