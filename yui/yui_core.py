"""
Yui Core — Chat com agentes isolados (Yui / Heathcliff).
- Yui e Heathcliff: ambos têm acesso a todas as tools (analisar código, workspace, etc).
"""

import asyncio
import json
import os
import queue
import threading
from typing import Any, AsyncIterator, Dict, Generator, List, Optional

from yui.agent_prompts import YUI_SYSTEM_PROMPT, HEATHCLIFF_SYSTEM_PROMPT

MAX_TOOL_ITERATIONS = 3

# Tools disponíveis para Yui e Heathcliff
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "analisar_codigo",
            "description": "Analisa código: vulnerabilidades, más práticas, arquitetura.",
            "parameters": {
                "type": "object",
                "properties": {"codigo": {"type": "string", "description": "Código fonte a analisar"}},
                "required": ["codigo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sugerir_arquitetura",
            "description": "Sugere estrutura de pastas e responsabilidades.",
            "parameters": {
                "type": "object",
                "properties": {"tipo_projeto": {"type": "string", "description": "web, api, mobile, fullstack, microsaas"}},
                "required": ["tipo_projeto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_custo_estimado",
            "description": "Calcula custo em USD/BRL por tokens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tokens_entrada": {"type": "integer"},
                    "tokens_saida": {"type": "integer"},
                },
                "required": ["tokens_entrada", "tokens_saida"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumir_contexto",
            "description": "Resumo técnico de conversa para memória.",
            "parameters": {
                "type": "object",
                "properties": {"conversa": {"type": "string"}},
                "required": ["conversa"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_arquivos_workspace",
            "description": "Lista arquivos do workspace (sandbox). Use para ver estrutura do projeto.",
            "parameters": {
                "type": "object",
                "properties": {"pasta": {"type": "string", "description": "Pasta relativa (ex: . ou src)"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ler_arquivo_workspace",
            "description": "Lê conteúdo de um arquivo do workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {"type": "string", "description": "Caminho relativo (ex: main.py)"},
                    "max_chars": {"type": "integer", "description": "Máx caracteres (default 8000)"},
                },
                "required": ["caminho"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escrever_arquivo_workspace",
            "description": "Escreve/modifica arquivo no workspace. Cria backup automático.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {"type": "string"},
                    "conteudo": {"type": "string"},
                },
                "required": ["caminho", "conteudo"],
            },
        },
    },
]


def _detect_tool_intent(texto: str) -> Optional[str]:
    """Tool Router: sugere tool_choice para Yui e Heathcliff."""
    t = (texto or "").lower()
    if any(x in t for x in ["código", "codigo", "analisar", "vulnerabilidade", "```", "função", "funcao"]):
        return "analisar_codigo"
    if any(x in t for x in ["arquitetura", "estrutura", "pastas", "projeto", "organizar"]):
        return "sugerir_arquitetura"
    if any(x in t for x in ["custo", "tokens", "preço", "preco", "quanto custa"]):
        return "calcular_custo_estimado"
    if any(x in t for x in ["resumir", "resumo", "histórico", "historico"]):
        return "resumir_contexto"
    if any(x in t for x in ["listar", "arquivos", "arquivo", "pasta", "workspace", "ver arquivos"]):
        return "listar_arquivos_workspace"
    if any(x in t for x in ["ler", "abrir", "conteúdo", "conteudo", "mostrar arquivo"]):
        return "ler_arquivo_workspace"
    if any(x in t for x in ["escrever", "modificar", "alterar", "criar arquivo", "salvar"]):
        return "escrever_arquivo_workspace"
    return None


def _executar_tool(nome: str, args: Dict[str, Any]) -> str:
    """Executa tool e retorna string. Fallback: retorna erro em JSON."""
    try:
        from yui.yui_tools import executar_tool
        r = executar_tool(nome, args)
        return json.dumps(r, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"ok": False, "erro": str(e)}, ensure_ascii=False)


def _resolve_agent(model: str, mensagem: str) -> str:
    """Resolve agente: auto → classificar_intencao; yui/heathcliff → direto."""
    m = (model or "yui").strip().lower()
    if m == "auto":
        from yui.intent_classifier import classificar_intencao
        return classificar_intencao(mensagem)
    if m == "heathcliff":
        return "heathcliff"
    return "yui"


def _build_workspace_context(active_files: Optional[List[str]] = None, console_errors: Optional[List[str]] = None, workspace_open: bool = False) -> str:
    """Monta contexto do workspace para injetar no prompt."""
    if not workspace_open and not active_files and not console_errors:
        return ""
    parts = []
    if workspace_open:
        parts.append("Workspace aberto.")
    if active_files:
        parts.append(f"Arquivos ativos no editor: {', '.join(active_files[:5])}")
    if console_errors:
        parts.append(f"Erros do console: {'; '.join(console_errors[:3])}")
    return "\n".join(parts) if parts else ""


async def stream_chat_agent(
    mensagem: str,
    agent: str,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    active_files: Optional[List[str]] = None,
    console_errors: Optional[List[str]] = None,
    workspace_open: bool = False,
) -> AsyncIterator[str]:
    """
    Chat em streaming. agent: "yui" | "heathcliff".
    Yui e Heathcliff: ambos têm acesso a todas as tools.
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    messages: List[Dict[str, Any]] = []

    if chat_id and user_id:
        from yui.memory_manager import build_context_for_chat
        ctx, _ = build_context_for_chat(chat_id, user_id, mensagem)
        if ctx:
            messages = ctx
        else:
            messages = [{"role": "user", "content": mensagem}]
    else:
        messages = [{"role": "user", "content": mensagem}]

    if agent == "yui":
        system = YUI_SYSTEM_PROMPT
    else:
        system = HEATHCLIFF_SYSTEM_PROMPT
    tools = TOOLS_SCHEMA
    intent = _detect_tool_intent(mensagem)
    tool_choice = {"type": "function", "function": {"name": intent}} if intent else "auto"

    sys_ctx = next((m.get("content", "") for m in messages if m.get("role") == "system"), None)
    if sys_ctx:
        system = system + "\n\nContexto resumido:\n" + sys_ctx
        messages = [m for m in messages if m.get("role") != "system"]
    ws_ctx = _build_workspace_context(active_files, console_errors, workspace_open)
    if ws_ctx:
        system = system + "\n\n[Workspace]\n" + ws_ctx
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": system})

    kwargs: Dict[str, Any] = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.2,
        "top_p": 1,
        "max_tokens": 800,
        "stream": True,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            stream = await client.chat.completions.create(**kwargs)
        except Exception:
            yield "Desculpe, ocorreu um erro. Tente novamente."
            return

        full_content = ""
        tool_calls_buf: List[Dict[str, Any]] = []

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content or ""
                yield delta.content or ""
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls or []:
                    idx = getattr(tc, "index", 0)
                    while len(tool_calls_buf) <= idx:
                        tool_calls_buf.append({"id": "", "name": "", "arguments": ""})
                    if getattr(tc, "id", None):
                        tool_calls_buf[idx]["id"] = tc.id
                    if getattr(tc, "name", None):
                        tool_calls_buf[idx]["name"] = tc.name
                    if getattr(tc, "arguments", None):
                        tool_calls_buf[idx]["arguments"] = tool_calls_buf[idx].get("arguments", "") + (tc.arguments or "")

        if not tool_calls_buf:
            if chat_id and user_id and full_content:
                from yui.memory_manager import save_message
                save_message(chat_id, "user", mensagem, user_id)
                save_message(chat_id, "assistant", full_content, user_id)
            return

        # Tool calls (só Heathcliff): executar e continuar
        msg = {"role": "assistant", "content": full_content or None, "tool_calls": []}
        for tc in tool_calls_buf:
            tid = tc.get("id", "")
            name = tc.get("name", "")
            args_str = tc.get("arguments", "{}")
            msg["tool_calls"].append({"id": tid, "function": {"name": name, "arguments": args_str}})
        messages.append(msg)
        for tc in tool_calls_buf:
            tid = tc.get("id", "")
            name = tc.get("name", "")
            args_str = tc.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else {}
            except json.JSONDecodeError:
                args = {}
            result = _executar_tool(name, args)
            messages.append({"role": "tool", "tool_call_id": tid, "content": result})
        kwargs["tool_choice"] = "auto"
        kwargs["messages"] = messages


def stream_chat_sync(
    mensagem: str,
    agent: str,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    active_files: Optional[List[str]] = None,
    console_errors: Optional[List[str]] = None,
    workspace_open: bool = False,
) -> Generator[str, None, None]:
    """Wrapper síncrono para stream_chat_agent."""
    q: queue.Queue = queue.Queue()

    def run_async():
        async def consume():
            try:
                async for chunk in stream_chat_agent(
                    mensagem, agent, chat_id, user_id,
                    active_files=active_files,
                    console_errors=console_errors,
                    workspace_open=workspace_open,
                ):
                    q.put(chunk)
            except Exception as e:
                q.put({"__error__": str(e)})
            finally:
                q.put(None)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(consume())
        except Exception as e:
            q.put({"__error__": str(e)})
            q.put(None)

    t = threading.Thread(target=run_async)
    t.start()
    while True:
        chunk = q.get()
        if chunk is None:
            break
        if isinstance(chunk, dict) and chunk.get("__error__"):
            raise RuntimeError(chunk.get("__error__", "Erro no stream"))
        yield chunk


# Compatibilidade
def stream_chat_yui_sync(
    mensagem: str,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    system_override: Optional[str] = None,
    model: str = "yui",
    active_files: Optional[List[str]] = None,
    console_errors: Optional[List[str]] = None,
    workspace_open: bool = False,
) -> Generator[str, None, None]:
    """Compat: usa classificar_intencao quando model=auto."""
    agent = _resolve_agent(model, mensagem)
    return stream_chat_sync(
        mensagem, agent, chat_id, user_id,
        active_files=active_files,
        console_errors=console_errors,
        workspace_open=workspace_open,
    )
