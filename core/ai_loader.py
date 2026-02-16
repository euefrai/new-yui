# ==========================================================
# YUI AI LOADER — Lazy loading do core da IA
#
# Não carrega OpenAI, planner, agent no start do servidor.
# Carrega só quando a primeira requisição de chat chega.
#
# Reduz memória inicial e evita SIGKILL no startup.
# ==========================================================

from typing import Any, Callable, Optional

_agent_controller: Optional[Callable] = None
_gerar_titulo_chat: Optional[Callable] = None
_detect_intent: Optional[Callable] = None
_tool_executor: Optional[Any] = None
_session_memory: Optional[Any] = None
_processar_texto_web: Optional[Callable] = None


def get_agent_controller():
    """Lazy: carrega agent_controller apenas na primeira chamada."""
    global _agent_controller
    if _agent_controller is None:
        from backend.ai.agent_controller import agent_controller
        _agent_controller = agent_controller
    return _agent_controller


def get_gerar_titulo_chat():
    """Lazy: carrega gerar_titulo_chat apenas na primeira chamada."""
    global _gerar_titulo_chat
    if _gerar_titulo_chat is None:
        from yui_ai.core.ai_engine import gerar_titulo_chat
        _gerar_titulo_chat = gerar_titulo_chat
    return _gerar_titulo_chat


def get_detect_intent():
    """Lazy: carrega detect_intent apenas na primeira chamada."""
    global _detect_intent
    if _detect_intent is None:
        from yui_ai.agent.router import detect_intent
        _detect_intent = detect_intent
    return _detect_intent


def get_tool_executor():
    """Lazy: carrega tool_executor apenas na primeira chamada."""
    global _tool_executor
    if _tool_executor is None:
        from yui_ai.agent.tool_executor import executor
        _tool_executor = executor
    return _tool_executor


def get_session_memory():
    """Lazy: carrega session_memory apenas na primeira chamada."""
    global _session_memory
    if _session_memory is None:
        from yui_ai.memory.session_memory import memory
        _session_memory = memory
    return _session_memory


def get_processar_texto_web():
    """Lazy: carrega processar_texto_web apenas na primeira chamada."""
    global _processar_texto_web
    if _processar_texto_web is None:
        from yui_ai.main import processar_texto_web
        _processar_texto_web = processar_texto_web
    return _processar_texto_web
