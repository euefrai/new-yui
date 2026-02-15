"""
AI Service — orquestração da IA (streaming, título, mensagem síncrona).

Rotas chamam o serviço; o serviço usa agent_controller, engine, yui_ai.
Route -> Service -> Core; rotas NÃO importam yui_ai.

Lazy loading: IA carrega só na primeira requisição (reduz RAM no startup).
Intent Router: porteiro — decide Local / Cache / Tools / LLM antes de tudo.
Local Brain + Cache Brain: 70% resolvido sem IA.
"""

import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Generator, Optional, Tuple

# Cache para buscas web (evita chamar DDGS repetidamente)
_WEB_CACHE: OrderedDict = OrderedDict()
_WEB_CACHE_LOCK = Lock()
_WEB_CACHE_MAX = 50
_WEB_CACHE_TTL = 300  # 5 min


def _web_cache_get(key: str) -> Optional[str]:
    with _WEB_CACHE_LOCK:
        if key not in _WEB_CACHE:
            return None
        entry = _WEB_CACHE[key]
        if (time.time() - entry["ts"]) > _WEB_CACHE_TTL:
            del _WEB_CACHE[key]
            return None
        _WEB_CACHE.move_to_end(key)
        return entry["value"]


def _web_cache_set(key: str, value: str) -> None:
    with _WEB_CACHE_LOCK:
        _WEB_CACHE[key] = {"value": value, "ts": time.time()}
        _WEB_CACHE.move_to_end(key)
        while len(_WEB_CACHE) > _WEB_CACHE_MAX:
            _WEB_CACHE.popitem(last=False)


def _responder_busca_web_local(message: str) -> Optional[str]:
    """Resposta factual rápida via tool buscar_web sem depender da LLM."""
    cached = _web_cache_get(message)
    if cached:
        return "(Resultado recente em cache)\n" + cached

    try:
        from core.tools_runtime import tool_buscar_web
        result = tool_buscar_web(message, limite=5)

        if not result or not result.get("ok"):
            return None

        itens = result.get("resultados") or []
        linhas = ["Encontrei isso na web:"]
        for i, r in enumerate(itens[:3], 1):
            link = r.get("url") or r.get("link") or ""
            titulo = r.get("titulo") or r.get("title") or "—"
            linhas.append(f"{i}. {titulo} - {link}")

        resposta = "\n".join(linhas)
        _web_cache_set(message, resposta)
        return resposta
    except Exception:
        return None


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
    """Streaming da resposta da YUI. Intent Router → Local → Cache → IA."""
    # Intent Router: roteia antes de tudo
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            resposta_local = responder_local(message)
            if resposta_local:
                yield resposta_local
                return
        if rota == "web_search":
            resposta_web = _responder_busca_web_local(message)
            if resposta_web:
                yield resposta_web
                return
    except Exception:
        pass

    # Local Brain (fallback para oi, etc)
    try:
        from yui_ai.core.local_brain import responder_local
        resposta_local = responder_local(message)
        if resposta_local:
            yield resposta_local
            return
    except Exception:
        pass

    # Cache Brain (Token Shield): perguntas repetidas = zero tokens
    try:
        from yui_ai.core.cache_brain import buscar_cache
        cached = buscar_cache(message)
        if cached:
            yield cached
            return
    except Exception:
        pass

    from core.ai_loader import get_agent_controller
    agent = get_agent_controller()
    full_reply: list[str] = []
    for chunk in agent(
        user_id, chat_id, message,
        model=model,
        confirm_high_cost=confirm_high_cost,
        active_files=active_files,
        console_errors=console_errors,
        workspace_open=workspace_open,
    ):
        full_reply.append(chunk)
        yield chunk

    # Salvar no cache para reutilizar
    reply = "".join(full_reply).strip()
    if reply:
        try:
            from yui_ai.core.cache_brain import salvar_cache
            salvar_cache(message, reply)
        except Exception:
            pass


def gerar_titulo_chat(first_message: str) -> str:
    """Gera título do chat a partir da primeira mensagem. Lazy loading."""
    from core.ai_loader import get_gerar_titulo_chat
    fn = get_gerar_titulo_chat()
    return (fn(first_message) or "").strip() or "Novo chat"


def processar_mensagem_sync(
    user_id: str, chat_id: str, message: str, model: str = "yui"
) -> str:
    """Resposta síncrona. Intent Router → Local → Cache → IA."""
    # Intent Router
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            resposta_local = responder_local(message)
            if resposta_local:
                return resposta_local
        if rota == "web_search":
            resposta_web = _responder_busca_web_local(message)
            if resposta_web:
                return resposta_web
    except Exception:
        pass

    # Local Brain
    try:
        from yui_ai.core.local_brain import responder_local
        resposta_local = responder_local(message)
        if resposta_local:
            return resposta_local
    except Exception:
        pass

    # Cache Brain (Token Shield)
    try:
        from yui_ai.core.cache_brain import buscar_cache
        cached = buscar_cache(message)
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

    # Salvar no cache para reutilizar
    if reply:
        try:
            from yui_ai.core.cache_brain import salvar_cache
            salvar_cache(message, reply)
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
    Orquestra o stream: Intent Router → Local → Cache → Tools → IA.
    """
    from core.ai_loader import get_session_memory, get_detect_intent, get_tool_executor
    session_memory = get_session_memory()

    # Intent Router: roteia antes de tudo
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            resposta_local = responder_local(message)
            if resposta_local:
                session_memory.add(user_id, "user", message)
                session_memory.add(user_id, "assistant", resposta_local)
                yield resposta_local
                return
        if rota == "web_search":
            resposta_web = _responder_busca_web_local(message)
            if resposta_web:
                session_memory.add(user_id, "user", message)
                session_memory.add(user_id, "assistant", resposta_web)
                yield resposta_web
                return
    except Exception:
        pass

    # Local Brain (fallback)
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

    # Cache Brain (Token Shield)
    try:
        from yui_ai.core.cache_brain import buscar_cache
        cached = buscar_cache(message)
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

    # Salvar no Cache Brain para reutilizar
    if reply:
        try:
            from yui_ai.core.cache_brain import salvar_cache
            salvar_cache(message, reply)
        except Exception:
            pass


def improve_message(prompt: str) -> Tuple[str, bool]:
    """Melhora um texto via IA. Lazy loading."""
    from core.ai_loader import get_processar_texto_web
    processar = get_processar_texto_web()
    resposta, _mid, api_key_missing = processar(prompt, reply_to_id=None)
    return (resposta or "").strip(), bool(api_key_missing)
