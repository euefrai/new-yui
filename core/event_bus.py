# ==========================================================
# YUI EVENT BUS — Sistema Nervoso Central
#
# Nenhum módulo chama outro direto. Tudo vira eventos.
# Planner → emit | Task Engine → emit | Reflection → escuta
#
# Em vez de: Planner chama Task, Task chama Context
# Agora:     Planner emite | Task emite | Reflection escuta
# ==========================================================

from typing import Any, Callable, Dict, List

_listeners: Dict[str, List[Callable[..., None]]] = {}

# Eventos padrão (para documentação e plugins)
EVENTS = (
    "memory_saved",
    "tool_executed",
    "response_generated",
    # Execution Graph
    "execution_node_start",
    "execution_node_done",
    "execution_node_failed",
    "execution_graph_done",
    "execution_graph_failed",
    # Sistema Nervoso (event-driven)
    "workspace_toggled",   # {open: bool}
    "file_changed",        # {path: str, action: str} — alias: arquivo_editado
    "agent_requested",     # {model, user_message}
    "preview_started",     # {}
    "memory_updated",      # {chat_id, user_id}
    "memory_update_requested",  # {root?} → scheduler adiciona indexar
    "task_queued",         # {task_id, fn_name} — alias: task_iniciada
    "task_iniciada",       # {task: str, task_id?, fn_name?} — início de task
    "task_done",           # {task_id, result}
    "task_failed",         # {task_id, error}
    "task_finished",       # {task_id, task_type, duration, success, error} — Reflection escuta
    "erro_detectado",      # {source: str, error: str, context?} — console, task, etc.
    "memoria_alta",        # {ram_mb: float, threshold: float} — Reflection Loop detectou
    "zip_ready",           # {download_url} — ZIP gerado em background
)


def subscribe(event: str, handler: Callable[..., None]) -> None:
    """Registra um handler para o evento. Pode ser chamado com *args, **kwargs."""
    if event not in _listeners:
        _listeners[event] = []
    _listeners[event].append(handler)


def unsubscribe(event: str, handler: Callable[..., None]) -> None:
    """Remove um handler do evento."""
    if event in _listeners:
        try:
            _listeners[event].remove(handler)
        except ValueError:
            pass


def emit(event: str, *args: Any, **kwargs: Any) -> None:
    """Dispara o evento para todos os handlers registrados. Erros são ignorados."""
    for fn in _listeners.get(event, []):
        try:
            fn(*args, **kwargs)
        except Exception:
            pass


def clear(event: str | None = None) -> None:
    """Remove todos os handlers de um evento, ou de todos se event for None."""
    if event is None:
        _listeners.clear()
    elif event in _listeners:
        _listeners[event] = []


def list_events() -> tuple:
    """Retorna a lista de eventos conhecidos (para plugins)."""
    return EVENTS


def on(event: str, handler: Callable[..., None]) -> None:
    """Alias para subscribe (API mais intuitiva)."""
    subscribe(event, handler)
