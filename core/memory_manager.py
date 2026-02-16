"""
MemoryManager: camada de conveniência sobre memory_events.

Responsabilidades:
- Registrar eventos curtos (mensagens recentes)
- Registrar fatos de longo prazo (perfil, preferências, decisões)
- Registrar resumos de chat (memória longa por chat)
- Montar um fragmento de contexto textual para o modelo
"""

from typing import Optional

from core.memory_events import MemoryTipo, buscar_eventos, registrar_evento


def add_event(user_id: str, chat_id: Optional[str], tipo: MemoryTipo, conteudo: str) -> None:
    """Wrapper direto para registrar_evento, com types corretos."""
    registrar_evento(user_id=user_id, chat_id=chat_id, tipo=tipo, conteudo=conteudo)


def add_fact(user_id: str, conteudo: str) -> None:
    """Fato de longo prazo sobre o usuário (sem chat_id)."""
    registrar_evento(user_id=user_id, chat_id=None, tipo="longa", conteudo=conteudo)


def add_summary(user_id: str, chat_id: str, conteudo: str) -> None:
    """Resumo de uma conversa específica (memória longa por chat)."""
    registrar_evento(user_id=user_id, chat_id=chat_id, tipo="longa", conteudo=conteudo)


def build_context_text(user_id: str, chat_id: Optional[str], limit_short: int = 10, limit_long: int = 10) -> str:
    """
    Monta um texto de contexto combinando:
    - memória longa (fatos/resumos) -> tipo='longa'
    - memória curta (eventos recentes desse chat) -> tipo='curta'
    """
    partes = []
    eventos_longos = buscar_eventos(user_id=user_id, chat_id=None, tipo="longa", limit=limit_long)
    if eventos_longos:
        partes.append("Fatos importantes e resumos anteriores sobre este usuário/projeto:")
        for ev in reversed(eventos_longos):
            partes.append(f"- {ev.get('conteudo', '')}")

    if chat_id:
        eventos_curta = buscar_eventos(user_id=user_id, chat_id=chat_id, tipo="curta", limit=limit_short)
    else:
        eventos_curta = []

    if eventos_curta:
        partes.append("")
        partes.append("Contexto recente desta conversa (últimos eventos):")
        for ev in reversed(eventos_curta):
            partes.append(f"- {ev.get('conteudo', '')}")

    return "\n".join(p for p in partes if p)

