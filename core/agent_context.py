"""
Contexto da execução atual do agente (user_id, chat_id).
Permite que tools como create_mission usem o contexto da sessão.
"""
from contextvars import ContextVar
from typing import Any, Optional

_current_user_id: ContextVar[str] = ContextVar("agent_user_id", default="")
_current_chat_id: ContextVar[str] = ContextVar("agent_chat_id", default="")
_current_execution_graph: ContextVar[Optional[Any]] = ContextVar("agent_execution_graph", default=None)


def set_agent_context(user_id: str = "", chat_id: str = "") -> None:
    """Define o contexto da sessão atual para as tools."""
    _current_user_id.set(user_id or "")
    _current_chat_id.set(chat_id or "")


def get_agent_context() -> tuple:
    """Retorna (user_id, chat_id) do contexto atual."""
    return (_current_user_id.get(), _current_chat_id.get())


def set_execution_graph(graph: Any) -> None:
    """Define o ExecutionGraph ativo (para UI de progresso)."""
    _current_execution_graph.set(graph)


def get_execution_graph() -> Optional[Any]:
    """Retorna o ExecutionGraph ativo ou None."""
    return _current_execution_graph.get()
