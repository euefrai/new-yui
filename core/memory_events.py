"""
Sistema de memória contextual por usuário.

Tabela no Supabase: memory_events

Campos principais:
- user_id  : UUID do usuário (auth.users.id)
- chat_id  : UUID do chat (opcional, referencia chats.id)
- tipo     : 'curta', 'longa' ou 'tecnica'
- conteudo : texto do evento (fato importante, resumo técnico, etc.)
"""

from typing import List, Optional, Literal, Dict, Any

from core.supabase_client import supabase


MemoryTipo = Literal["curta", "longa", "tecnica"]


def registrar_evento(
    user_id: str,
    chat_id: Optional[str],
    tipo: MemoryTipo,
    conteudo: str,
) -> None:
    """
    Registra um evento de memória no Supabase.
    Não levanta erro se Supabase não estiver configurado.
    """
    if not supabase:
        return
    if not user_id or not conteudo:
        return
    if tipo not in ("curta", "longa", "tecnica"):
        tipo = "curta"
    row: Dict[str, Any] = {
        "user_id": user_id,
        "tipo": tipo,
        "conteudo": conteudo,
    }
    if chat_id:
        row["chat_id"] = chat_id
    try:
        supabase.table("memory_events").insert(row).execute()
    except Exception:
        # Falha de memória não deve quebrar fluxo principal
        return


def buscar_eventos(
    user_id: str,
    chat_id: Optional[str] = None,
    tipo: Optional[MemoryTipo] = None,
    limit: int = 20,
) -> List[dict]:
    """
    Busca eventos de memória mais recentes para um usuário (e opcionalmente chat/tipo).
    """
    if not supabase or not user_id:
        return []
    try:
        q = supabase.table("memory_events").select("*").eq("user_id", user_id)
        if chat_id:
            q = q.eq("chat_id", chat_id)
        if tipo:
            q = q.eq("tipo", tipo)
        res = (
            q.order("created_at", desc=True)
            .limit(max(1, min(limit, 100)))
            .execute()
        )
        return res.data or []
    except Exception:
        return []

