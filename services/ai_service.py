"""
AI Service — Orquestração da IA (streaming, título, mensagem síncrona).
Fluxo: Route -> Service -> Core (Lazy Loading & Intent Router).
"""

from typing import Any, Generator, Optional, Tuple

def _responder_busca_web_local(message: str) -> Optional[str]:
    """Resposta factual rápida via tool buscar_web sem depender da LLM."""
    try:
        from core.tools_runtime import tool_buscar_web
        result = tool_buscar_web(message, limite=5)
        
        if not result or not result.get("ok"):
            error = (result or {}).get("error") if isinstance(result, dict) else None
            detalhe = f" Detalhe: {error}." if error else ""
            return (
                "Não consegui consultar a web neste momento. "
                "Tente novamente em instantes ou reformule sua pergunta com mais contexto."
                + detalhe
            )

        itens = result.get("resultados") or []
        if not itens:
            return "Não achei resultados confiáveis agora. Tente reformular a pergunta."
        
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
        return "\n".join(linhas)
    except Exception:
        return "Erro ao processar busca local. Tente novamente."

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
    """Streaming da resposta: Intent Router → Local → Cache → IA."""
    
    # 1. Intent Router & Local Brain (Economia de Tokens)
    try:
        from yui_ai.core.intent_router import decidir_rota
        from yui_ai.core.local_brain import responder_local
        rota = decidir_rota(message)
        
        if rota == "web_search":
            yield _responder_busca_web_local(message)
            return
            
        if rota in ("time", "zip_builder", "terminal", "deploy"):
            res = responder_local(message)
            if res:
                yield res
                return
    except Exception: pass

    # 2. Cache Brain (Token Shield)
    try:
        from yui_ai.core.cache_brain import buscar_cache
        cached = buscar_cache(message)
        if cached:
            yield cached
            return
    except Exception: pass

    # 3. LLM Agent (Processamento Real)
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

    # 4. Salvar no Cache
    reply = "".join(full_reply).strip()
    if reply:
        try:
            from yui_ai.core.cache_brain import salvar_cache
            salvar_cache(message, reply)
        except Exception: pass

def handle_chat_stream(
    user_id: str, chat_id: str, message: str, **kwargs
) -> Generator[str, None, None]:
    """Orquestrador mestre para rotas de Chat."""
    from core.ai_loader import get_session_memory
    session_memory = get_session_memory()

    # Tenta resolver via lógica local/cache primeiro
    # (Mesma lógica do stream_resposta, mas gerenciando memória de sessão)
    full_text = ""
    for chunk in stream_resposta(user_id, chat_id, message, **kwargs):
        full_text += chunk
        yield chunk

    if full_text:
        session_memory.add(user_id, "user", message)
        session_memory.add(user_id, "assistant", full_text)

def gerar_titulo_chat(first_message: str) -> str:
    from core.ai_loader import get_gerar_titulo_chat
    fn = get_gerar_titulo_chat()
    return (fn(first_message) or "").strip() or "Novo chat"

def improve_message(prompt: str) -> Tuple[str, bool]:
    from core.ai_loader import get_processar_texto_web
    processar = get_processar_texto_web()
    resposta, _mid, api_key_missing = processar(prompt, reply_to_id=None)
    return (resposta or "").strip(), bool(api_key_missing)