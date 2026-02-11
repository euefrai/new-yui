# ==========================================================
# YUI CONTEXT ENGINE
# Motor central de contexto: escolhe o que enviar à IA.
# Camadas: short_term_context, long_term_memory, system_state, user_profile.
# ==========================================================

from typing import Any, Dict, List

from core.memory import get_messages
from core.memory_manager import build_context_text
from core.self_state import to_prompt_snippet as self_state_snippet
from core.user_profile import get_user_profile

from backend.ai.context_builder import montar_contexto_projeto
from backend.ai.context_memory import buscar_contexto as buscar_contexto_chat
from backend.ai.vector_memory import buscar_contexto as buscar_contexto_vetorial

# Limites padrão (ajustáveis)
MAX_MENSAGENS_HISTORICO = 15
LIMITE_CURTA = 8
LIMITE_LONGA = 8
VETORIAL_LIMITE = 5


def montar_contexto_ia(
    user_id: str,
    chat_id: str,
    user_message: str,
    raiz_projeto: str = ".",
    max_mensagens: int = MAX_MENSAGENS_HISTORICO,
    limite_vetorial: int = VETORIAL_LIMITE,
) -> Dict[str, Any]:
    """
    Monta todo o contexto que a IA precisa (contexto inteligente em camadas).

    Retorna:
        historico, contexto_projeto, memoria_vetorial, contexto_chat_anterior, memoria_eventos
        short_term_context: str — resumo/últimas trocas (janela curta)
        long_term_memory: str — memória vetorial + eventos (longo prazo)
        system_state: str — estado interno da Yui (self_state)
        user_profile: dict — perfil do usuário (nível, linguagens, modo)
    """
    out: Dict[str, Any] = {
        "historico": [],
        "contexto_projeto": "",
        "memoria_vetorial": "",
        "contexto_chat_anterior": "",
        "memoria_eventos": "",
        "short_term_context": "",
        "long_term_memory": "",
        "system_state": "",
        "user_profile": {},
    }

    # Histórico do chat (limitado) = base para short_term
    raw = get_messages(chat_id, user_id) or []
    if raw:
        window = raw[-max_mensagens * 2 :] if len(raw) > max_mensagens * 2 else raw
        out["historico"] = [
            {"role": m.get("role", "user"), "content": (m.get("content") or "")}
            for m in window
        ]
        # short_term: últimas mensagens em texto (para contexto rápido)
        parts = []
        for m in window[-6:]:
            role = m.get("role", "user")
            content = (m.get("content") or "")[:500]
            parts.append(f"[{role}]: {content}")
        out["short_term_context"] = "\n".join(parts) if parts else ""

    # Contexto do projeto (arquivos)
    try:
        out["contexto_projeto"] = montar_contexto_projeto(raiz_projeto) or ""
    except Exception:
        out["contexto_projeto"] = ""

    # Memória vetorial (trechos relevantes à pergunta)
    try:
        out["memoria_vetorial"] = buscar_contexto_vetorial(user_message, limite=limite_vetorial) or ""
    except Exception:
        out["memoria_vetorial"] = ""

    # Contexto de respostas anteriores deste chat (RAM)
    try:
        out["contexto_chat_anterior"] = buscar_contexto_chat(chat_id, user_message) or ""
    except Exception:
        out["contexto_chat_anterior"] = ""

    # Memória de eventos (curta + longa)
    try:
        out["memoria_eventos"] = build_context_text(
            user_id=user_id,
            chat_id=chat_id,
            limit_short=LIMITE_CURTA,
            limit_long=LIMITE_LONGA,
        ) or ""
    except Exception:
        out["memoria_eventos"] = ""

    # long_term_memory: vetorial + eventos (contexto de longo prazo)
    out["long_term_memory"] = (
        (out["memoria_vetorial"] + "\n\n" + out["memoria_eventos"]).strip()
        or ""
    )

    # system_state: estado interno da Yui (última ação, erro, confiança, modo)
    try:
        out["system_state"] = self_state_snippet()
    except Exception:
        out["system_state"] = ""

    # user_profile: nível técnico, linguagens, modo de resposta
    try:
        out["user_profile"] = get_user_profile(user_id) or {}
    except Exception:
        out["user_profile"] = {}

    return out
