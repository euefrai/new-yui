"""
AI Service — Orquestração da IA (streaming, título, mensagem síncrona).
Fluxo: Route -> Service -> Core (Lazy Loading & Intent Router).
Controle de Custo: Cache de Busca Web e Cache de Respostas (Token Shield).
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
            error = (result or {}).get("error") if isinstance(result, dict) else None
            detalhe = f" Detalhe: {error}." if error else ""
            return f"Não consegui consultar a web agora.{detalhe}"

        itens = result.get("resultados") or []
        if not itens:
            return "Não achei resultados confiáveis para essa pergunta."

        linhas = ["Encontrei isso na web:"]
        for i, r in enumerate(itens[:5], 1):
            titulo = (r.get("titulo") or r.get("title") or "Sem título").strip()
            link = (r.get("link") or r.get("url") or r.get("href") or "").strip()
            resumo = (r.get("resumo") or r.get("snippet") or r.get("body") or "").strip()
            bloco = f"{i}. {titulo}"
            if resumo:
                bloco += f" — {resumo}"
            if link:
                bloco += f"\n   Fonte: {link}"
            linhas.append(bloco)

        resposta = "\n".join(linhas)
        _web_cache_set(message, resposta)
        return resposta
    except Exception:
        return (
            "Não consegui consultar a web neste momento. "
            "Tente novamente em instantes ou reformule sua pergunta com mais contexto."
        )


def stream_resposta(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
    confirm_high_cost: bool = False,
    active_files: Optional[list] = None,
    console_errors: Optional[list] = None,
    workspace_open: bool = False,
    **kwargs
) -> Generator[str, None, None]:
    """Streaming da resposta: Intent Router → Local → Cache → IA."""
    # 1. Intent Router
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        if rota == "web_search":
            resposta_web = _responder_busca_web_local(message)
            if resposta_web:
                yield resposta_web
                return
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            resposta_local = responder_local(message)
            if resposta_local:
                yield resposta_local
                return
    except Exception:
        pass

    # 2. Local Brain (fallback)
    try:
        from yui_ai.core.local_brain import responder_local
        resposta_local = responder_local(message)
        if resposta_local:
            yield resposta_local
            return
    except Exception:
        pass

    # 3. Cache Brain (chave: user_id + message + resumo_contexto)
    resumo_ctx = None
    try:
        if chat_id and user_id:
            from yui.memory_manager import build_context_for_chat
            _, resumo_ctx = build_context_for_chat(chat_id, user_id, message)
        from yui_ai.core.cache_brain import buscar_cache
        cached = buscar_cache(message, user_id=user_id, resumo_contexto=resumo_ctx)
        if cached:
            yield cached
            return
    except Exception:
        pass

    # 4. LLM Agent — Yui/Heathcliff com classificação de intenção
    try:
        from yui.yui_core import stream_chat_yui_sync
        full_reply: list[str] = []
        for chunk in stream_chat_yui_sync(
            message,
            chat_id=chat_id,
            user_id=user_id,
            model=model,
        ):
            full_reply.append(chunk)
            yield chunk
        reply = "".join(full_reply).strip()
    except Exception:
        from core.ai_loader import get_agent_controller
        agent = get_agent_controller()
        full_reply = []
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
        reply = "".join(full_reply).strip()

    # 5. Salvar no cache (chave única)
    if reply:
        try:
            from yui_ai.core.cache_brain import salvar_cache
            salvar_cache(message, reply, user_id=user_id, resumo_contexto=resumo_ctx)
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
    full_text = ""
    for chunk in stream_resposta(user_id, chat_id, message, model=model):
        full_text += chunk
    return full_text


def handle_chat_stream(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
    confirm_high_cost: bool = False,
    active_files: Optional[list] = None,
    console_errors: Optional[list] = None,
    workspace_open: bool = False,
    **kwargs
) -> Generator[str, None, None]:
    """Orquestra o stream: Intent Router → Local → Cache → Tools → IA."""
    from core.ai_loader import get_session_memory, get_detect_intent, get_tool_executor
    session_memory = get_session_memory()

    # Intent Router
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        if rota == "web_search":
            resposta_web = _responder_busca_web_local(message)
            if resposta_web:
                session_memory.add(user_id, "user", message)
                session_memory.add(user_id, "assistant", resposta_web)
                yield resposta_web
                return
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            resposta_local = responder_local(message)
            if resposta_local:
                session_memory.add(user_id, "user", message)
                session_memory.add(user_id, "assistant", resposta_local)
                yield resposta_local
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

    # Cache Brain (chave: user_id + message + resumo)
    resumo_ctx = None
    try:
        if chat_id and user_id:
            from yui.memory_manager import build_context_for_chat
            _, resumo_ctx = build_context_for_chat(chat_id, user_id, message)
        from yui_ai.core.cache_brain import buscar_cache
        cached = buscar_cache(message, user_id=user_id, resumo_contexto=resumo_ctx)
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

    if reply:
        try:
            from yui_ai.core.cache_brain import salvar_cache
            salvar_cache(message, reply, user_id=user_id, resumo_contexto=resumo_ctx)
        except Exception:
            pass


def improve_message(prompt: str) -> Tuple[str, bool]:
    """Melhora um texto via IA. Lazy loading."""
    from core.ai_loader import get_processar_texto_web
    processar = get_processar_texto_web()
    resposta, _mid, api_key_missing = processar(prompt, reply_to_id=None)
    return (resposta or "").strip(), bool(api_key_missing)
