# IA: delega para a camada services da raiz (agent_controller, engine).
from services.ai_service import (
    gerar_titulo_chat,
    processar_mensagem_sync,
    stream_resposta,
)

__all__ = ["gerar_titulo_chat", "processar_mensagem_sync", "stream_resposta"]
