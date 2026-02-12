# ==========================================================
# YUI SYSTEM STATE ENGINE
# Cérebro de estado do sistema — consistência operacional.
#
# Separa projetos amadores de plataformas reais:
# - Evita módulos rodando quando não deveriam
# - Reduz RAM, CPU e comportamento aleatório
# ==========================================================

import threading
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SystemState:
    """
    Estado global do sistema. Controle central — nada mágico.

    Uso:
        if state.workspace_open:
            enable_editor_features()
        if state.executing_graph:
            activate_observer()
    """
    mode: str = "chat"  # "chat" | "editor" | "executor" | "terminal"
    workspace_open: bool = False
    executing_graph: bool = False
    terminal_sessions_alive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "workspace_open": self.workspace_open,
            "executing_graph": self.executing_graph,
            "terminal_sessions_alive": self.terminal_sessions_alive,
        }


_state = SystemState()
_lock = threading.Lock()


def get_state() -> SystemState:
    """Retorna o estado atual (thread-safe)."""
    with _lock:
        return SystemState(
            mode=_state.mode,
            workspace_open=_state.workspace_open,
            executing_graph=_state.executing_graph,
            terminal_sessions_alive=_state.terminal_sessions_alive,
        )


def set_mode(mode: str) -> None:
    """Define o modo: chat, editor, executor, terminal."""
    with _lock:
        _state.mode = mode


def set_workspace_open(open: bool) -> None:
    """Workspace (editor + árvore) está aberto."""
    with _lock:
        _state.workspace_open = open


def set_executing_graph(executing: bool) -> None:
    """Execution Graph está em execução."""
    with _lock:
        _state.executing_graph = executing


def set_terminal_sessions_alive(alive: bool) -> None:
    """Há sessões de terminal ativas."""
    with _lock:
        _state.terminal_sessions_alive = alive


def update(workspace_open: bool | None = None, mode: str | None = None) -> None:
    """Atualiza múltiplos campos de uma vez."""
    with _lock:
        if workspace_open is not None:
            _state.workspace_open = workspace_open
        if mode is not None:
            _state.mode = mode


# ==========================================================
# Helpers para decisões
# ==========================================================

def should_enable_editor_features() -> bool:
    """Editor/Preview só quando workspace está aberto."""
    return get_state().workspace_open


def should_activate_observer() -> bool:
    """Observer ativo quando Execution Graph está rodando."""
    return get_state().executing_graph


def should_load_heavy_context() -> bool:
    """Context pesado (context_kernel recursivo etc) só quando workspace aberto."""
    return get_state().workspace_open
