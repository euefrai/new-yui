"""
Core Engine — Cérebro central da Yui.

Workspace + Runtime + Memória + Agente = Mini DevOS.

Módulos:
- action_router: roteia ações (editor, terminal, analyzer, RAG)
- context_kernel: unifica contexto em tempo real
"""

from core.engine.action_router import route_action, ActionIntent
from core.engine.context_kernel import get_context_snapshot, ContextSnapshot, snapshot_to_prompt

__all__ = [
    "route_action",
    "ActionIntent",
    "get_context_snapshot",
    "ContextSnapshot",
    "snapshot_to_prompt",
]
