"""
Chat Service — camada de abstração sobre chats e mensagens.
Usa yui_ai.services.memory_service (interface única: Supabase ou JSON local).
Rotas só chamam o serviço; nenhum acesso direto ao JSON.
"""

from typing import Any, Dict, List, Optional

from core.supabase_client import get_supabase_client
from yui_ai.services import memory_service as mem


def supabase_available() -> bool:
    """True se o backend tem cliente Supabase (service key)."""
    return get_supabase_client("service") is not None


def chat_pertence_usuario(chat_id: str, user_id: str) -> bool:
    return mem.chat_belongs_to_user(chat_id, user_id)


def mensagem_pertence_usuario(message_id: str, user_id: str) -> bool:
    return mem.message_belongs_to_user(message_id, user_id)


def criar_chat(user_id: str) -> Optional[Dict[str, Any]]:
    return mem.create_chat(user_id)


def listar_chats(user_id: str) -> List[Dict[str, Any]]:
    return mem.get_chats(user_id) or []


def carregar_historico(chat_id: str, user_id: str) -> List[Dict[str, Any]]:
    return mem.load_history(chat_id, user_id) or []


def salvar_mensagem(chat_id: str, role: str, content: str, user_id: Optional[str] = None) -> None:
    mem.save_message(chat_id, role, content or "", user_id)


def atualizar_titulo_chat(chat_id: str, titulo: str, user_id: str) -> bool:
    if not chat_pertence_usuario(chat_id, user_id):
        return False
    mem.update_chat_title(chat_id, titulo, user_id)
    return True


def deletar_chat(chat_id: str, user_id: str) -> bool:
    return mem.delete_chat(chat_id, user_id)


def obter_mensagem_para_edicao(message_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    return mem.get_message_for_edit(message_id, user_id)


def atualizar_mensagem(message_id: str, content: str, user_id: str) -> bool:
    return mem.update_message(message_id, content, user_id)


def remover_mensagem(message_id: str, user_id: str) -> bool:
    return mem.remove_message(message_id, user_id)
