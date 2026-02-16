"""
Constrói string de contexto a partir das últimas mensagens da memória.
Usado antes de enviar o prompt à IA para manter coerência da conversa.
"""

from yui_ai.memory import chat_memory

CONTEXT_LIMIT = 8


def build_context(limit: int = CONTEXT_LIMIT) -> str:
    """
    Pega as últimas `limit` mensagens da memória e monta uma string de contexto
    para a IA (quem disse o quê).
    """
    mensagens = chat_memory.get_context(limit=limit)
    if not mensagens:
        return ""

    partes = []
    for m in mensagens:
        autor = (m.get("autor") or "").strip() or "?"
        conteudo = (m.get("conteudo") or "").strip()
        if not conteudo:
            continue
        # Limita tamanho por mensagem para não estourar o prompt
        if len(conteudo) > 600:
            conteudo = conteudo[:597] + "..."
        label = "Usuário" if autor == "usuario" else "Yui"
        partes.append(f"{label}: {conteudo}")

    if not partes:
        return ""
    return "Últimas mensagens do chat:\n" + "\n".join(partes) + "\n\n"
