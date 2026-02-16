# ==========================================================
# YUI CONTEXT ENGINE — Memória Operacional (RAM)
#
# NÃO é memória longa. NÃO vai pro banco. NÃO vai pro RAG.
# Só existe enquanto a sessão está viva.
#
# Evita: IA esquece workspace, Planner recalcula tudo, CPU sobe.
# Permite: Heathcliff "lembra" o que está fazendo.
#
# Fluxo: Intent → Context Engine → Planner → Task
# ==========================================================

import threading
from collections import defaultdict
from typing import Any, Dict, Optional


_Sessions: Dict[str, Dict[str, Any]] = defaultdict(dict)
_lock = threading.Lock()


def _session_key(user_id: str, chat_id: Optional[str] = None) -> str:
    k = str(user_id or "")
    if chat_id:
        k = f"{k}:{chat_id}"
    return k


class ContextEngine:
    """
    Memória operacional por sessão.
    set/get/clear — não persiste.
    """

    def __init__(self, user_id: str = "", chat_id: Optional[str] = None):
        self.user_id = user_id
        self.chat_id = chat_id

    def set(self, chave: str, valor: Any) -> None:
        self._state()[chave] = valor

    def get(self, chave: str, default: Any = None) -> Any:
        return self._state().get(chave, default)

    def clear(self) -> None:
        self._state().clear()

    def _state(self) -> Dict[str, Any]:
        k = _session_key(self.user_id, self.chat_id)
        with _lock:
            if k not in _Sessions:
                _Sessions[k] = {}
            return _Sessions[k]

    def to_dict(self) -> Dict[str, Any]:
        """Retorna cópia do estado."""
        return dict(self._state())

    def to_prompt_snippet(self) -> str:
        """Snippet para injetar no prompt da IA."""
        state = self.to_dict()
        if not state:
            return ""
        parts = []
        if state.get("modo"):
            parts.append(f"Modo atual: {state['modo']}")
        if state.get("arquivo_aberto"):
            parts.append(f"Arquivo aberto: {state['arquivo_aberto']}")
        if state.get("task_ativa"):
            parts.append(f"Task em foco: {state['task_ativa']}")
        if state.get("workspace_open") is True:
            parts.append("Workspace aberto (evite recriar estrutura)")
        # Persona Router: quem está ativo (Yui ou Heathcliff)
        persona = state.get("persona_ativa")
        if persona == "heathcliff":
            parts.append("Persona: Heathcliff (respostas técnicas e concisas)")
        elif persona == "yui":
            parts.append("Persona: Yui (respostas amigáveis e didáticas)")
        # Reflection Loop: estado do servidor (modo economia, dividir tasks)
        try:
            from core.reflection_loop import get_estado_reflexao
            reflexao = get_estado_reflexao()
            if reflexao == "modo_economia":
                parts.append("Servidor em modo economia (RAM alta): gere menos código por vez.")
            elif reflexao == "dividir_tasks":
                parts.append("Servidor lento: prefira tarefas menores e sequenciais.")
        except Exception:
            pass
        out = "[Estado operacional] " + ". ".join(parts) + "\n\n" if parts else ""
        # Workspace Index: mapa do projeto (quando disponível)
        mapa = state.get("workspace_map")
        if mapa and isinstance(mapa, dict) and mapa.get("total", 0) > 0:
            try:
                from core.workspace_indexer import to_prompt_snippet as ws_snippet
                out += ws_snippet(mapa, state.get("arquivo_aberto"))
            except Exception:
                pass
        return out


# --- API funcional (para uso sem instância) ---

def get_context(user_id: str, chat_id: Optional[str] = None) -> ContextEngine:
    """Retorna engine para a sessão."""
    return ContextEngine(user_id, chat_id)


def get(user_id: str, chave: str, default: Any = None, chat_id: Optional[str] = None) -> Any:
    """Atalho: get value."""
    return get_context(user_id, chat_id).get(chave, default)


def set(user_id: str, chave: str, valor: Any, chat_id: Optional[str] = None) -> None:
    """Atalho: set value."""
    get_context(user_id, chat_id).set(chave, valor)


def clear_session(user_id: str, chat_id: Optional[str] = None) -> None:
    """Remove sessão (ex: clear_chat)."""
    k = _session_key(user_id, chat_id)
    with _lock:
        if chat_id:
            if k in _Sessions:
                del _Sessions[k]
        else:
            prefix = str(user_id)
            to_remove = [key for key in _Sessions if key == prefix or key.startswith(prefix + ":")]
            for key in to_remove:
                del _Sessions[key]


def update_from_snapshot(
    user_id: str,
    workspace_open: Optional[bool] = None,
    active_files: Optional[list] = None,
    chat_id: Optional[str] = None,
) -> None:
    """Atualiza contexto a partir de snapshot do frontend."""
    ctx = get_context(user_id, chat_id)
    if workspace_open is not None:
        ctx.set("workspace_open", workspace_open)
        ctx.set("modo", "workspace" if workspace_open else "chat")
        if workspace_open:
            try:
                from core.workspace_indexer import scan
                ctx.set("workspace_map", scan())
            except Exception:
                pass
    if active_files and len(active_files) > 0:
        arquivo = active_files[0] if isinstance(active_files[0], str) else str(active_files[0])
        ctx.set("arquivo_aberto", arquivo)
