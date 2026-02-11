"""
AI Service — orquestração da IA (streaming, título, mensagem síncrona).

Rotas chamam o serviço; o serviço usa agent_controller, engine, yui_ai.
"""

from typing import Any, Generator, Optional

from backend.ai.agent_controller import agent_controller
from core.engine import process_message as engine_process_message
from yui_ai.core.ai_engine import gerar_titulo_chat as _gerar_titulo_chat


def stream_resposta(
    user_id: str,
    chat_id: str,
    message: str,
) -> Generator[str, None, None]:
    """Streaming da resposta da YUI (Agent Controller)."""
    yield from agent_controller(user_id, chat_id, message)


def gerar_titulo_chat(first_message: str) -> str:
    """Gera título do chat a partir da primeira mensagem."""
    return ( _gerar_titulo_chat(first_message) or "" ).strip() or "Novo chat"


def processar_mensagem_sync(user_id: str, chat_id: str, message: str) -> str:
    """Resposta síncrona (engine legado, ex.: /api/send)."""
    return ( engine_process_message(user_id, chat_id, message) or "" ).strip()
