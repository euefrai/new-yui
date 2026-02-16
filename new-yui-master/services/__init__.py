# Camada de serviços: abstração entre rotas e core/backend.
# Rotas chamam serviços; serviços chamam core, Supabase, IA.

from services.chat_service import (
    chat_pertence_usuario,
    criar_chat,
    deletar_chat,
    listar_chats,
    carregar_historico,
    salvar_mensagem,
    atualizar_titulo_chat,
    mensagem_pertence_usuario,
)
from services.ai_service import stream_resposta, gerar_titulo_chat, processar_mensagem_sync

__all__ = [
    "chat_pertence_usuario",
    "criar_chat",
    "deletar_chat",
    "listar_chats",
    "carregar_historico",
    "salvar_mensagem",
    "atualizar_titulo_chat",
    "mensagem_pertence_usuario",
    "stream_resposta",
    "gerar_titulo_chat",
    "processar_mensagem_sync",
]
