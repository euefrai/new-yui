"""
AI Service — orquestração da IA (streaming, título, mensagem síncrona).

Rotas chamam o serviço; o serviço usa agent_controller, engine, yui_ai.
Route -> Service -> Core; rotas NÃO importam yui_ai.

Lazy loading: IA carrega só na primeira requisição (reduz RAM no startup).
Cache: respostas curtas (oi, obrigado) evitam chamar IA de novo.
Local Brain: respostas triviais (horas, oi, zipar) sem gastar tokens.
"""

from typing import Any, Generator, Optional, Tuple


def stream_resposta(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
    confirm_high_cost: bool = False,
    active_files: Optional[list] = None,
    console_errors: Optional[list] = None,
    workspace_open: bool = False,
) -> Generator[str, None, None]:
    """Streaming da resposta da YUI (Agent Controller). Lazy loading + cache + Local Brain."""
    # Local Brain: responde trivialidades sem gastar tokens
    try:
        from yui_ai.core.local_brain import responder_local
        resposta_local = responder_local(message)
        if resposta_local:
            yield resposta_local
            return
    except Exception:
        pass

    try:
        from core.response_cache import get as cache_get, should_cache, set as cache_set
        cached = cache_get(message)
        if cached:
            yield cached
            return
    except Exception:
        pass

    from core.ai_loader import get_agent_controller
    agent = get_agent_controller()
    yield from agent(
        user_id, chat_id, message,
        model=model,
        confirm_high_cost=confirm_high_cost,
        active_files=active_files,
        console_errors=console_errors,
        workspace_open=workspace_open,
    )


def gerar_titulo_chat(first_message: str) -> str:
    """Gera título do chat a partir da primeira mensagem. Lazy loading."""
    from core.ai_loader import get_gerar_titulo_chat
    fn = get_gerar_titulo_chat()
    return (fn(first_message) or "").strip() or "Novo chat"


def processar_mensagem_sync(
    user_id: str, chat_id: str, message: str, model: str = "yui"
) -> str:
    """Resposta síncrona; usa agent_controller. Lazy loading + cache + Local Brain."""
    # Local Brain: responde trivialidades sem gastar tokens
    try:
        from yui_ai.core.local_brain import responder_local
        resposta_local = responder_local(message)
        if resposta_local:
            return resposta_local
    except Exception:
        pass

    try:
        from core.response_cache import get as cache_get, should_cache, set as cache_set
        cached = cache_get(message)
        if cached:
            return cached
    except Exception:
        pass

    from core.ai_loader import get_agent_controller
    agent = get_agent_controller()
    full: list[str] = []
    for chunk in agent(user_id, chat_id, message, model=model):
        full.append(chunk)
    reply = "".join(full).strip()

    try:
        from core.response_cache import should_cache, set as cache_set
        if should_cache(message) and reply:
            cache_set(message, reply)
    except Exception:
        pass
    return reply


def handle_chat_stream(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
    confirm_high_cost: bool = False,
    active_files: Optional[list] = None,
    console_errors: Optional[list] = None,
    workspace_open: bool = False,
) -> Generator[str, None, None]:
    """
    Orquestra o stream do chat: Local Brain, cache, intent, tool ou IA. Lazy loading.
    """
    from core.ai_loader import get_session_memory, get_detect_intent, get_tool_executor
    session_memory = get_session_memory()

    # Local Brain: responde trivialidades sem gastar tokens
    try:
        from yui_ai.core.local_brain import responder_local
        resposta_local = responder_local(message)
        if resposta_local:
            session_memory.add(user_id, "user", message)
            session_memory.add(user_id, "assistant", resposta_local)
            yield resposta_local
            return
    except Exception:
        pass

    # Cache: resposta pronta para prompts curtos
    try:
        from core.response_cache import get as cache_get, should_cache, set as cache_set
        cached = cache_get(message)
        if cached:
            session_memory.add(user_id, "user", message)
            session_memory.add(user_id, "assistant", cached)
            yield cached
            return
    except Exception:
        pass

    session_memory.add(user_id, "user", message)
    detect_intent = get_detect_intent()
    intent = detect_intent(message)

    if intent != "chat":
        tool_executor = get_tool_executor()
        tool_result = tool_executor.execute(intent, message)
        if tool_result:
            msg = tool_result.get("message") or str(tool_result)
            if msg and "nenhum resultado" not in msg.lower():
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
        workspace_open=workspace_open,
    ):
        full_reply.append(chunk)
        yield chunk

    reply = "".join(full_reply)
    session_memory.add(user_id, "assistant", reply)

    # Cache resposta para prompts curtos
    try:
        from core.response_cache import should_cache, set as cache_set
        if should_cache(message) and reply:
            cache_set(message, reply)
    except Exception:
        pass


def improve_message(prompt: str) -> Tuple[str, bool]:
    """Melhora um texto via IA. Lazy loading."""
    from core.ai_loader import get_processar_texto_web
    processar = get_processar_texto_web()
    resposta, _mid, api_key_missing = processar(prompt, reply_to_id=None)
    return (resposta or "").strip(), bool(api_key_missing)
