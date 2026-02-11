"""
Chat Service — camada de abstração sobre chats e mensagens.

A rota só chama o serviço; o serviço usa core.memory (Supabase).
Isolamento de ownership (user_id) e ponto único para evoluir (ex.: Tool Agent).
"""

from typing import Any, Dict, List, Optional

from core.memory import (
    chat_belongs_to_user,
    create_chat as _create_chat,
    get_chats as _get_chats,
    get_messages as _get_messages,
    message_belongs_to_user as _message_belongs_to_user,
    save_message as _save_message,
    update_chat_title as _update_chat_title,
)
from core.supabase_client import supabase


def chat_pertence_usuario(chat_id: str, user_id: str) -> bool:
    """True se o chat existe e pertence ao user_id."""
    return bool(chat_belongs_to_user(chat_id, user_id))


def mensagem_pertence_usuario(message_id: str, user_id: str) -> bool:
    """True se a mensagem existe e pertence a um chat do user_id."""
    return bool(_message_belongs_to_user(message_id, user_id))


def criar_chat(user_id: str) -> Optional[Dict[str, Any]]:
    """Cria um novo chat para o usuário. Retorna o chat ou None."""
    return _create_chat(user_id)


def listar_chats(user_id: str) -> List[Dict[str, Any]]:
    """Lista chats do usuário, mais recentes primeiro."""
    return _get_chats(user_id) or []


def carregar_historico(chat_id: str, user_id: str) -> List[Dict[str, Any]]:
    """Carrega mensagens do chat (só se o chat pertencer ao user_id)."""
    return _get_messages(chat_id, user_id) or []


def salvar_mensagem(chat_id: str, role: str, content: str, user_id: Optional[str] = None) -> None:
    """Salva mensagem no chat. Se user_id for passado, valida ownership."""
    _save_message(chat_id, role, content or "", user_id)


def atualizar_titulo_chat(chat_id: str, titulo: str, user_id: str) -> bool:
    """Atualiza o título do chat. Retorna True se atualizou."""
    if not chat_pertence_usuario(chat_id, user_id):
        return False
    _update_chat_title(chat_id, titulo, user_id)
    return True


def deletar_chat(chat_id: str, user_id: str) -> bool:
    """Remove o chat. Retorna True se removeu."""
    if not supabase or not chat_pertence_usuario(chat_id, user_id):
        return False
    try:
        supabase.table("chats").delete().eq("id", chat_id).eq("user_id", user_id).execute()
        return True
    except Exception:
        return False


def obter_mensagem_para_edicao(message_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Retorna a mensagem se existir e pertencer ao usuário."""
    if not mensagem_pertence_usuario(message_id, user_id):
        return None
    if not supabase:
        return None
    try:
        res = supabase.table("messages").select("*").eq("id", message_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def atualizar_mensagem(message_id: str, content: str, user_id: str) -> bool:
    """Atualiza o conteúdo da mensagem. Retorna True se atualizou."""
    if not mensagem_pertence_usuario(message_id, user_id):
        return False
    if not supabase:
        return False
    try:
        supabase.table("messages").update({"content": content}).eq("id", message_id).execute()
        return True
    except Exception:
        return False


def remover_mensagem(message_id: str, user_id: str) -> bool:
    """Remove a mensagem. Retorna True se removeu."""
    if not mensagem_pertence_usuario(message_id, user_id):
        return False
    if not supabase:
        return False
    try:
        supabase.table("messages").delete().eq("id", message_id).execute()
        return True
    except Exception:
        return False
