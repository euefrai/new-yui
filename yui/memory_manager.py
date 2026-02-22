"""
Yui Memory Manager — Resumo e controle de histórico.
- SEMPRE usa apenas: resumo (se existir) + última mensagem do usuário
- Nunca reutiliza resposta anterior como nova pergunta
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


def build_context_for_chat(
    chat_id: str,
    user_id: Optional[str] = None,
    ultima_pergunta: str = "",
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Monta o contexto SEMPRE com: resumo (se houver) + última pergunta.
    Nunca envia histórico completo. Nunca reutiliza resposta anterior como pergunta.
    Retorna: (messages, resumo_usado)
    """
    msgs = get_messages(chat_id, user_id, limit=MSG_LIMIT + 20)
    if not msgs:
        return [{"role": "user", "content": ultima_pergunta or ""}], None

    formatted: List[Dict[str, str]] = []
    for m in msgs:
        role = (m.get("role") or "user").lower()
        if role not in ("user", "assistant", "system"):
            role = "user"
        content = (m.get("content") or "").strip()
        if content:
            formatted.append({"role": role, "content": content})

    # A mensagem atual (ultima_pergunta) é a nova pergunta do usuário — sempre usá-la
    user_content = (ultima_pergunta or "").strip()
    if not user_content and formatted:
        for m in reversed(formatted):
            if m.get("role") == "user":
                user_content = m.get("content", "") or ""
                break

    # Sempre resumir histórico (evitar vazamento de contexto)
    conversa_para_resumo = "\n".join(
        f"{m['role']}: {m['content'][:400]}" for m in formatted
    )
    if not conversa_para_resumo.strip():
        return [{"role": "user", "content": user_content}], None

    from yui.yui_tools import resumir_contexto
    result = resumir_contexto(conversa_para_resumo)
    resumo = result.get("resumo", conversa_para_resumo[:1500]) if result.get("ok") else conversa_para_resumo[:1500]

    # Sempre: resumo + última pergunta (nunca histórico completo)
    messages = [
        {"role": "system", "content": f"Contexto resumido da conversa anterior:\n{resumo}"},
        {"role": "user", "content": user_content},
    ]
    return messages, resumo
