# ==========================================================
# YUI SESSION MANAGER
# Sessão inteligente — pensamento atual por usuário.
#
# Memória = banco histórico (longo prazo)
# Sessão = pensamento atual (curto prazo, em RAM)
#
# request → Session Manager → IA recebe contexto já pronto
# Menos processamento, menos RAM, respostas mais rápidas.
#
# Por ora: sessão em RAM (dict). Depois: Redis Session Store.
# ==========================================================

from collections import defaultdict
from threading import Lock
from typing import Any, Dict, Optional

_sessoes: Dict[str, Dict[str, Any]] = defaultdict(dict)
_lock = Lock()

# Limite para evitar sessões gigantes
MAX_CONTEXTO_LEN = 2000
MAX_HISTORICO_RECENTE = 5


def get_session(user_id: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna sessão do usuário. Se chat_id, retorna sub-sessão do chat.
    Sessão vazia = dict mutável; updates funcionam.
    """
    key = str(user_id or "")
    if chat_id:
        key = f"{user_id}:{chat_id}"
    with _lock:
        if key not in _sessoes:
            _sessoes[key] = _new_session()
        return _sessoes[key]


def _new_session() -> Dict[str, Any]:
    """Cria sessão vazia com estrutura padrão."""
    return {
        "contexto": "",           # resumo do contexto atual
        "ultimo_topico": "",      # último tópico discutido
        "ultima_intencao": "",    # última intenção detectada
        "historico_recente": [],  # últimas N trocas [user, assistant]
        "chat_id": None,
        "updated_at": None,
    }


def update_session(
    user_id: str,
    data: Dict[str, Any],
    chat_id: Optional[str] = None,
) -> None:
    """Atualiza sessão. data é mergeado no dict existente."""
    session = get_session(user_id, chat_id)
    with _lock:
        for k, v in data.items():
            if k == "historico_recente" and isinstance(v, list):
                session[k] = v[-MAX_HISTORICO_RECENTE:]
            elif k == "contexto" and isinstance(v, str) and len(v) > MAX_CONTEXTO_LEN:
                session[k] = v[-MAX_CONTEXTO_LEN:]
            else:
                session[k] = v
        import time
        session["updated_at"] = time.time()


def get_contexto(user_id: str, chat_id: Optional[str] = None) -> str:
    """Retorna contexto da sessão (pronto para prompt)."""
    s = get_session(user_id, chat_id)
    # Usa historico_recente (pensamento atual) ou contexto manual
    recent = s.get("historico_recente") or []
    if recent:
        parts = []
        for t in recent:
            u = (t.get("user") or "").strip()
            a = (t.get("assistant") or "").strip()
            if u:
                parts.append(f"User: {u[:200]}")
            if a:
                parts.append(f"Yui: {a[:300]}")
        if parts:
            return "[Contexto atual da sessão — últimas trocas]\n" + "\n".join(parts[-6:]) + "\n\n"
    ctx = (s.get("contexto") or "").strip()
    if ctx:
        return f"[Contexto atual da sessão]\n{ctx}\n\n"
    return ""


def set_contexto(
    user_id: str,
    contexto: str,
    chat_id: Optional[str] = None,
) -> None:
    """Define contexto da sessão (após resposta da IA)."""
    if not contexto or not isinstance(contexto, str):
        return
    if len(contexto) > MAX_CONTEXTO_LEN:
        contexto = "..." + contexto[-MAX_CONTEXTO_LEN:]
    update_session(user_id, {"contexto": contexto}, chat_id)


def append_turn(
    user_id: str,
    user_msg: str,
    assistant_msg: str,
    chat_id: Optional[str] = None,
) -> None:
    """Adiciona uma troca ao histórico recente da sessão."""
    session = get_session(user_id, chat_id)
    recent = list(session.get("historico_recente") or [])
    recent.append({"user": (user_msg or "")[:300], "assistant": (assistant_msg or "")[:500]})
    update_session(user_id, {"historico_recente": recent}, chat_id)


def clear_session(user_id: str, chat_id: Optional[str] = None) -> None:
    """Limpa sessão (ex: quando usuário limpa chat)."""
    with _lock:
        if chat_id:
            key = f"{user_id}:{chat_id}"
            if key in _sessoes:
                del _sessoes[key]
        else:
            # Remove todas as sessões do usuário
            prefix = str(user_id)
            to_remove = [k for k in _sessoes if k == prefix or k.startswith(prefix + ":")]
            for k in to_remove:
                del _sessoes[k]


def session_count() -> int:
    """Quantidade de sessões ativas (útil para debug)."""
    with _lock:
        return len(_sessoes)
