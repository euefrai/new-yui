# ==========================================================
# YUI CONTEXT MEMORY AGENT
# Guarda respostas recentes e permite reutilizar contexto
# (memória em RAM por chat — não substitui o histórico do Supabase)
# ==========================================================

import time
from collections import deque
from typing import Dict

# Memória em RAM por sessão (simples e rápida)
# session_id = chat_id (um deque por conversa)
MEMORIA_SESSAO: Dict[str, deque] = {}

MAX_ITENS = 12  # quantidade máxima por chat (evita RAM infinito)


def salvar_memoria(session_id: str, conteudo: str) -> None:
    """Salva respostas recentes da Yui para reutilização futura."""
    if not session_id or not (conteudo or "").strip():
        return
    if session_id not in MEMORIA_SESSAO:
        MEMORIA_SESSAO[session_id] = deque(maxlen=MAX_ITENS)
    MEMORIA_SESSAO[session_id].append({
        "conteudo": (conteudo or "").strip(),
        "timestamp": time.time(),
    })


def buscar_contexto(session_id: str, texto_usuario: str) -> str:
    """Procura no histórico recente do chat algo relacionado à mensagem do usuário."""
    if not session_id or not (texto_usuario or "").strip():
        return ""
    if session_id not in MEMORIA_SESSAO:
        return ""

    texto_busca = texto_usuario.lower().strip()
    palavras = [p for p in texto_busca.split() if len(p) > 1]
    if not palavras:
        return ""

    resultados: list = []
    for item in MEMORIA_SESSAO[session_id]:
        conteudo = (item.get("conteudo") or "").lower()
        if any(p in conteudo for p in palavras):
            resultados.append(item.get("conteudo") or "")

    if not resultados:
        return ""
    # retorna os últimos 3 relevantes
    return "\n\n".join(resultados[-3:])
