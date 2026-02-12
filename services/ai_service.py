"""
AI Service — orquestração da IA (streaming, título, mensagem síncrona).

Rotas chamam o serviço; o serviço usa agent_controller, engine, yui_ai.
Route -> Service -> Core; rotas NÃO importam yui_ai.
"""

from typing import Any, Generator, Optional, Tuple

from backend.ai.agent_controller import agent_controller
from yui_ai.agent.router import detect_intent
from yui_ai.agent.tool_executor import executor as tool_executor
from yui_ai.core.ai_engine import gerar_titulo_chat as _gerar_titulo_chat
from yui_ai.memory.session_memory import memory as session_memory


def stream_resposta(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
    confirm_high_cost: bool = False,
    active_files: Optional[list] = None,
    console_errors: Optional[list] = None,
) -> Generator[str, None, None]:
    """Streaming da resposta da YUI (Agent Controller)."""
    yield from agent_controller(
        user_id, chat_id, message,
        model=model,
        confirm_high_cost=confirm_high_cost,
        active_files=active_files,
        console_errors=console_errors,
    )


def gerar_titulo_chat(first_message: str) -> str:
    """Gera título do chat a partir da primeira mensagem."""
    return (_gerar_titulo_chat(first_message) or "").strip() or "Novo chat"


def processar_mensagem_sync(
    user_id: str, chat_id: str, message: str, model: str = "yui"
) -> str:
    """Resposta síncrona; usa agent_controller para consistência com stream."""
    full: list[str] = []
    for chunk in agent_controller(user_id, chat_id, message, model=model):
        full.append(chunk)
    return "".join(full).strip()


def handle_chat_stream(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
    confirm_high_cost: bool = False,
    active_files: Optional[list] = None,
    console_errors: Optional[list] = None,
) -> Generator[str, None, None]:
    """
    Orquestra o stream do chat: intent, tool ou IA, session_memory.
    Retorna gerador de chunks (texto); a rota formata em SSE.
    """
    session_memory.add(user_id, "user", message)
    intent = detect_intent(message)
    if intent != "chat":
        tool_result = tool_executor.execute(intent, message)
        if tool_result:
            msg = tool_result.get("message") or str(tool_result)
            session_memory.add(user_id, "assistant", msg)
            yield msg
            return
    full_reply = []
    for chunk in stream_resposta(
        user_id, chat_id, message,
        model=model,
        confirm_high_cost=confirm_high_cost,
        active_files=active_files,
        console_errors=console_errors,
    ):
        full_reply.append(chunk)
        yield chunk
    session_memory.add(user_id, "assistant", "".join(full_reply))


def improve_message(prompt: str) -> Tuple[str, bool]:
    """
    Melhora um texto via IA. Retorna (resposta, api_key_missing).
    """
    from yui_ai.main import processar_texto_web
    resposta, _mid, api_key_missing = processar_texto_web(prompt, reply_to_id=None)
    return (resposta or "").strip(), bool(api_key_missing)
