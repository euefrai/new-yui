"""
AI Service — Orquestração da IA (streaming, título, mensagem síncrona).
Fluxo: Route -> Service -> Core (Lazy Loading & Intent Router).
Controle de Custo: Cache de Busca Web e Cache de Respostas (Token Shield).
"""

from typing import Any, Generator, Optional, Tuple
import time


_WEB_SEARCH_CACHE: dict[str, tuple[float, str]] = {}
_WEB_SEARCH_CACHE_TTL = 900


def _web_cache_get(query: str) -> Optional[str]:
    key = (query or "").strip().lower()
    if not key:
        return None
    item = _WEB_SEARCH_CACHE.get(key)
    if not item:
        return None
# --- Cache de Busca Web (Evita requisições redundantes à API de Busca) ---
_WEB_SEARCH_CACHE: dict[str, tuple[float, str]] = {}
_WEB_SEARCH_CACHE_TTL = 900  # 15 minutos

def _web_cache_get(query: str) -> Optional[str]:
    key = (query or "").strip().lower()
    if not key: return None
    item = _WEB_SEARCH_CACHE.get(key)
    if not item: return None
    ts, text = item
    if (time.time() - ts) > _WEB_SEARCH_CACHE_TTL:
        _WEB_SEARCH_CACHE.pop(key, None)
        return None
    return text


def _web_cache_set(query: str, text: str) -> None:
    key = (query or "").strip().lower()
    if not key or not text:
        return
    _WEB_SEARCH_CACHE[key] = (time.time(), text)



def _responder_busca_web_local(message: str) -> Optional[str]:
    """Resposta factual rápida via tool buscar_web sem depender da LLM."""
    try:
        from core.tools_runtime import tool_buscar_web
        result = tool_buscar_web(message, limite=5)
        if not result or not result.get("ok"):
            cached = _web_cache_get(message)
            if cached:
                return "(Resultado recente em cache)\n" + cached
            error = (result or {}).get("error") if isinstance(result, dict) else None
            detalhe = f" Detalhe: {error}." if error else ""
            return (
                "Não consegui consultar a web neste momento. "
                "Tente novamente em instantes ou reformule sua pergunta com mais contexto."
                + detalhe
            )
        itens = result.get("resultados") or []
        if not itens:
            return "Não achei resultados confiáveis agora. Tente reformular a pergunta com mais contexto."
def _web_cache_set(query: str, text: str) -> None:
    key = (query or "").strip().lower()
    if not key or not text: return
    _WEB_SEARCH_CACHE[key] = (time.time(), text)

# --- Processadores Locais ---

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
            
            bloco = f"{i}. {titulo}"
            if resumo: bloco += f" — {resumo}"
            if link: bloco += f"\n   Fonte: {link}"
            linhas.append(bloco)
        
        resposta = "\n".join(linhas)
        _web_cache_set(message, resposta)
        return resposta
    except Exception:
        return (
            "Não consegui consultar a web neste momento. "
            "Tente novamente em instantes ou reformule sua pergunta com mais contexto."
        )
        return "Erro ao processar busca local. Tente novamente."

# --- Orquestração de Respostas ---

def stream_resposta(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
    **kwargs
) -> Generator[str, None, None]:
    """Streaming da resposta: Intent Router → Local → Cache → IA."""
    
    # 1. Roteador de Intenção (Economia de Tokens e Latência)
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        if rota == "web_search":
            resposta_web = _responder_busca_web_local(message)
            if resposta_web:
                yield resposta_web
                return
        
        if rota == "web_search":
            yield _responder_busca_web_local(message)
            return
            
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            res = responder_local(message)
            if res:
                yield res
                return
    except Exception: pass

    # 2. Cache Brain (Token Shield - Respostas idênticas recentes)
    try:
        from yui_ai.core.cache_brain import buscar_cache
        cached = buscar_cache(message)
        if cached:
            yield cached
            return
    except Exception: pass

    # 3. LLM Agent (Processamento Real via Anthropic/OpenAI)
    from core.ai_loader import get_agent_controller
    agent = get_agent_controller()
    full_reply = []
    
    for chunk in agent(user_id, chat_id, message, model=model, **kwargs):
        full_reply.append(chunk)
        yield chunk

    # 4. Persistência em Cache (Pós-processamento)
    reply = "".join(full_reply).strip()
    if reply:
        try:
            from yui_ai.core.cache_brain import salvar_cache
            salvar_cache(message, reply)
        except Exception: pass

def processar_mensagem_sync(
    user_id: str, chat_id: str, message: str, model: str = "yui"
) -> str:
    """Resposta síncrona. Intent Router → Local → Cache → IA."""
    # Intent Router
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        if rota == "web_search":
            resposta_web = _responder_busca_web_local(message)
            if resposta_web:
                return resposta_web
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            resposta_local = responder_local(message)
            if resposta_local:
                return resposta_local
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

    """Versão síncrona simplificada que reusa a lógica de stream."""
    full_text = ""
    for chunk in stream_resposta(user_id, chat_id, message, model=model):
        full_text += chunk
    return full_text

def handle_chat_stream(
    user_id: str, chat_id: str, message: str, **kwargs
) -> Generator[str, None, None]:
    """Orquestrador mestre com persistência automática em memória de sessão."""
    from core.ai_loader import get_session_memory
    session_memory = get_session_memory()

    # Intent Router: roteia antes de tudo
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
    full_text = ""
    for chunk in stream_resposta(user_id, chat_id, message, **kwargs):
        full_text += chunk
        yield chunk

    if full_text:
        session_memory.add(user_id, "user", message)
        session_memory.add(user_id, "assistant", full_text)

# --- Funções Auxiliares ---

def gerar_titulo_chat(first_message: str) -> str:
    """Gera um título curto para a conversa baseado na primeira mensagem."""
    from core.ai_loader import get_gerar_titulo_chat
    fn = get_gerar_titulo_chat()
    return (fn(first_message) or "").strip() or "Novo chat"

def improve_message(prompt: str) -> Tuple[str, bool]:
    """Refina o prompt do usuário antes do envio (Magic Wand)."""
    from core.ai_loader import get_processar_texto_web
    processar = get_processar_texto_web()
    resposta, _mid, api_key_missing = processar(prompt, reply_to_id=None)
    return (resposta or "").strip(), bool(api_key_missing)