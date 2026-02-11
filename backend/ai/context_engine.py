# ==========================================================
# YUI CONTEXT ENGINE
# Motor central de contexto: escolhe o que enviar à IA.
# Últimas N mensagens + resumo + memória relevante (evita custo e melhora resposta).
# ==========================================================

from typing import Any, Dict, List

from core.memory import get_messages
from core.memory_manager import build_context_text

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
    Monta todo o contexto que a IA precisa em um único lugar.

    Retorna:
        historico: list[ {role, content} ] — últimas mensagens do chat
        contexto_projeto: str — arquivos/estrutura do projeto
        memoria_vetorial: str — trechos relevantes (ChromaDB)
        contexto_chat_anterior: str — respostas anteriores relevantes (context_memory)
        memoria_eventos: str — fatos e eventos recentes (memory_manager)
    """
    out: Dict[str, Any] = {
        "historico": [],
        "contexto_projeto": "",
        "memoria_vetorial": "",
        "contexto_chat_anterior": "",
        "memoria_eventos": "",
    }

    # Histórico do chat (limitado)
    raw = get_messages(chat_id, user_id) or []
    if raw:
        window = raw[-max_mensagens * 2 :] if len(raw) > max_mensagens * 2 else raw
        out["historico"] = [
            {"role": m.get("role", "user"), "content": (m.get("content") or "")}
            for m in window
        ]

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

    return out
