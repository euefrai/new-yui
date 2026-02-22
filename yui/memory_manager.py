"""
Yui Memory Manager — Resumo e controle de histórico.
- Armazena histórico no banco (core.memory)
- Se histórico > 10 mensagens, resumir usando resumir_contexto
- Usa apenas resumo + última pergunta para economizar tokens
"""

from typing import Any, Dict, List, Optional

MSG_LIMIT = 10


def get_messages(chat_id: str, user_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Busca mensagens do chat no banco."""
    try:
        from core.memory import get_messages as _get
        return _get(chat_id, user_id, limit) or []
    except Exception:
        return []


def save_message(chat_id: str, role: str, content: str, user_id: Optional[str] = None) -> None:
    """Salva mensagem no banco."""
    try:
        from core.memory import save_message as _save
        _save(chat_id, role, content, user_id)
    except Exception:
        pass


def build_context_for_yui(
    chat_id: str,
    user_id: Optional[str] = None,
    ultima_pergunta: str = "",
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Monta o contexto otimizado para a Yui.
    - Se histórico <= 10 mensagens: retorna mensagens formatadas para a API
    - Se histórico > 10: usa resumir_contexto e retorna [system com resumo] + [user com última pergunta]
    Retorna: (messages, resumo_usado)
    """
    msgs = get_messages(chat_id, user_id, limit=MSG_LIMIT + 20)
    if not msgs:
        return [], None

    # Formatar para formato OpenAI
    formatted: List[Dict[str, str]] = []
    for m in msgs:
        role = (m.get("role") or "user").lower()
        if role not in ("user", "assistant", "system"):
            role = "user"
        content = (m.get("content") or "").strip()
        if content:
            formatted.append({"role": role, "content": content})

    if len(formatted) <= MSG_LIMIT:
        return formatted, None

    # Histórico grande: resumir
    conversa_texto = "\n".join(
        f"{m['role']}: {m['content'][:500]}" for m in formatted[:-1]
    )
    from yui.yui_tools import resumir_contexto
    result = resumir_contexto(conversa_texto)
    resumo = result.get("resumo", conversa_texto[:1500]) if result.get("ok") else conversa_texto[:1500]

    # Retornar apenas: resumo como system + última pergunta como user
    messages = [
        {"role": "system", "content": f"Contexto resumido da conversa anterior:\n{resumo}"},
        {"role": "user", "content": ultima_pergunta or (formatted[-1].get("content", "") if formatted else "")},
    ]
    return messages, resumo


def append_and_maybe_summarize(
    chat_id: str,
    role: str,
    content: str,
    user_id: Optional[str] = None,
) -> None:
    """Salva mensagem e, se histórico > 10, pode acionar resumo na próxima chamada."""
    save_message(chat_id, role, content, user_id)
