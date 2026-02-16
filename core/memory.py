"""
Sistema de memória por usuário: chats e mensagens no Supabase.
Hierarquia: user (auth.users) → chats (sessões) → messages.
Sempre validar que o chat pertence ao user antes de ler/escrever mensagens.
"""
from core.supabase_client import supabase


def chat_belongs_to_user(chat_id, user_id):
    """Retorna True se o chat existe e pertence ao user_id. Essencial para isolar dados por usuário."""
    if not supabase or not chat_id or not user_id:
        return False
    try:
        r = supabase.table("chats").select("id").eq("id", chat_id).eq("user_id", user_id).limit(1).execute()
        return bool(r.data and len(r.data) > 0)
    except Exception:
        return False


def create_chat(user_id):
    if not supabase:
        return None
    data = supabase.table("chats").insert({
        "user_id": user_id,
        "titulo": "Novo chat"
    }).execute()
    return data.data[0] if data.data else None


def get_chats(user_id):
    if not supabase:
        return []
    data = supabase.table("chats").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return data.data or []


def save_message(chat_id, role, content, user_id=None):
    """Salva mensagem no chat. Se user_id for passado, só grava se o chat pertencer ao usuário."""
    if not supabase:
        return
    if user_id is not None and not chat_belongs_to_user(chat_id, user_id):
        return
    supabase.table("messages").insert({
        "chat_id": chat_id,
        "role": role,
        "content": content or ""
    }).execute()


def get_messages(chat_id, user_id=None, limit=None):
    """
    Lista mensagens do chat. Se user_id for passado, só retorna se o chat pertencer ao usuário.
    limit: se informado, retorna só as últimas N mensagens (reduz RAM em servidores 2GB).
    """
    if not supabase:
        return []
    if user_id is not None and not chat_belongs_to_user(chat_id, user_id):
        return []
    if limit:
        data = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=True).limit(limit).execute()
        msgs = (data.data or [])[::-1]
        return msgs
    data = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=False).execute()
    return data.data or []


def update_chat_title(chat_id, titulo, user_id=None):
    """Atualiza título do chat. Se user_id for passado, só atualiza se o chat pertencer ao usuário."""
    if not supabase:
        return
    if user_id is not None and not chat_belongs_to_user(chat_id, user_id):
        return
    supabase.table("chats").update({"titulo": titulo}).eq("id", chat_id).execute()


def message_belongs_to_user(message_id, user_id):
    """Retorna True se a mensagem existe e pertence a um chat do user_id."""
    if not supabase or not message_id or not user_id:
        return False
    try:
        r = supabase.table("messages").select("chat_id").eq("id", message_id).limit(1).execute()
        if not r.data or len(r.data) == 0:
            return False
        return chat_belongs_to_user(r.data[0]["chat_id"], user_id)
    except Exception:
        return False
