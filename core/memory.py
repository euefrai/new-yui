"""
Sistema de memória por usuário: chats e mensagens no Supabase.
Compatível com o schema existente (chats.titulo, messages sem user_id).
"""
from core.supabase_client import supabase


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


def save_message(chat_id, role, content):
    if not supabase:
        return
    supabase.table("messages").insert({
        "chat_id": chat_id,
        "role": role,
        "content": content or ""
    }).execute()


def get_messages(chat_id):
    if not supabase:
        return []
    data = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=False).execute()
    return data.data or []


def update_chat_title(chat_id, titulo):
    if not supabase:
        return
    supabase.table("chats").update({"titulo": titulo}).eq("id", chat_id).execute()
