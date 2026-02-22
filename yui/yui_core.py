"""
Yui Core — Chat + Tool Routing com OpenAI function calling.
- model: gpt-4o-mini
- temperature=0.2, top_p=1, max_tokens=800
- Tool Use real com fallback
"""

import asyncio
import json
import os
import queue
import threading
from typing import Any, AsyncIterator, Dict, Generator, List, Optional

SYSTEM_PROMPT = """Você é Yui, uma engenheira de software especialista.
Regras:
- Seja técnica e objetiva.
- Priorize segurança e escalabilidade.
- Explique raciocínio de forma estruturada.
- Não invente bibliotecas inexistentes.
- Se não souber, diga explicitamente.
- Sugira melhorias arquiteturais quando possível.
- Use ferramentas sempre que for mais adequado do que responder direto."""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "analisar_codigo",
            "description": "Analisa código: detecta vulnerabilidades, más práticas, problemas de arquitetura.",
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
            "description": "Sugere estrutura ideal de pastas e responsabilidades para um tipo de projeto.",
            "parameters": {
                "type": "object",
                "properties": {"tipo_projeto": {"type": "string", "description": "Ex: web, api, mobile, fullstack, microsaas"}},
                "required": ["tipo_projeto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_custo_estimado",
            "description": "Calcula estimativa de custo em USD/BRL baseado em tokens de entrada e saída.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tokens_entrada": {"type": "integer", "description": "Número de tokens de input"},
                    "tokens_saida": {"type": "integer", "description": "Número de tokens de output"},
                },
                "required": ["tokens_entrada", "tokens_saida"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumir_contexto",
            "description": "Gera resumo técnico curto de uma conversa para memória.",
            "parameters": {
                "type": "object",
                "properties": {"conversa": {"type": "string", "description": "Texto da conversa a resumir"}},
                "required": ["conversa"],
            },
        },
    },
]


def _detect_intent(texto: str) -> Optional[str]:
    """Tool Router: detecta intenção para sugerir tool_choice."""
    t = (texto or "").lower()
    if any(x in t for x in ["código", "codigo", "analisar", "vulnerabilidade", "```", "função", "funcao"]):
        return "analisar_codigo"
    if any(x in t for x in ["arquitetura", "estrutura", "pastas", "projeto", "organizar"]):
        return "sugerir_arquitetura"
    if any(x in t for x in ["custo", "tokens", "preço", "preco", "quanto custa"]):
        return "calcular_custo_estimado"
    if any(x in t for x in ["resumir", "resumo", "histórico", "historico"]):
        return "resumir_contexto"
    return None


def _executar_tool(nome: str, args: Dict[str, Any]) -> str:
    """Executa tool e retorna string para o modelo."""
    try:
        from yui.yui_tools import executar_tool
        r = executar_tool(nome, args)
        return json.dumps(r, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"ok": False, "erro": str(e)}, ensure_ascii=False)


def chat_yui(
    mensagem: str,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    system_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Chat síncrono com Tool Use.
    Retorna: {ok, texto, tool_calls, usage}
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    messages: List[Dict[str, Any]] = []
    if chat_id and user_id:
        from yui.memory_manager import build_context_for_yui
        ctx, _ = build_context_for_yui(chat_id, user_id, mensagem)
        if ctx:
            messages = ctx
        else:
            messages = [{"role": "user", "content": mensagem}]
    else:
        messages = [{"role": "user", "content": mensagem}]

    system = system_override or SYSTEM_PROMPT
    sys_ctx = next((m.get("content", "") for m in messages if m.get("role") == "system"), None)
    if sys_ctx:
        system = system + "\n\nContexto resumido:\n" + sys_ctx
        messages = [m for m in messages if m.get("role") != "system"]
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": system})

    intent = _detect_intent(mensagem)
    tool_choice = "auto"
    if intent:
        tool_choice = {"type": "function", "function": {"name": intent}}

    max_iter = 3
    for _ in range(max_iter):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice=tool_choice,
            temperature=0.2,
            top_p=1,
            max_tokens=800,
        )
        choice = resp.choices[0] if resp.choices else None
        if not choice:
            return {"ok": False, "texto": "Sem resposta.", "tool_calls": [], "usage": {}}

        msg = choice.message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            texto = (msg.content or "").strip()
            if chat_id and user_id and texto:
                from yui.memory_manager import save_message
                save_message(chat_id, "user", mensagem, user_id)
                save_message(chat_id, "assistant", texto, user_id)
            return {
                "ok": True,
                "texto": texto,
                "tool_calls": [],
                "usage": getattr(resp, "usage", None) and {
                    "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
                } or {},
            }

        # Executar tools
        messages.append(msg)
        for tc in tool_calls:
            name = tc.function.name if hasattr(tc.function, "name") else tc.get("function", {}).get("name", "")
            args_str = tc.function.arguments if hasattr(tc.function, "arguments") else tc.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
            except json.JSONDecodeError:
                args = {}
            result = _executar_tool(name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": getattr(tc, "id", "") or tc.get("id", ""),
                "content": result,
            })
        tool_choice = "auto"

    return {"ok": False, "texto": "Limite de iterações de tools atingido.", "tool_calls": [], "usage": {}}


async def stream_chat_yui(
    mensagem: str,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    system_override: Optional[str] = None,
) -> AsyncIterator[str]:
    """
    Chat em streaming. Em caso de tool calls, executa e faz nova chamada;
    o streaming é da resposta final.
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    messages: List[Dict[str, Any]] = []
    if chat_id and user_id:
        from yui.memory_manager import build_context_for_yui
        ctx, _ = build_context_for_yui(chat_id, user_id, mensagem)
        if ctx:
            messages = ctx
        else:
            messages = [{"role": "user", "content": mensagem}]
    else:
        messages = [{"role": "user", "content": mensagem}]

    system = system_override or SYSTEM_PROMPT
    sys_ctx = next((m.get("content", "") for m in messages if m.get("role") == "system"), None)
    if sys_ctx:
        system = system + "\n\nContexto resumido:\n" + sys_ctx
        messages = [m for m in messages if m.get("role") != "system"]
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": system})

    intent = _detect_intent(mensagem)
    tool_choice = "auto"
    if intent:
        tool_choice = {"type": "function", "function": {"name": intent}}

    max_iter = 3
    for _ in range(max_iter):
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice=tool_choice,
            temperature=0.2,
            top_p=1,
            max_tokens=800,
            stream=True,
        )

        full_content = ""
        tool_calls_buf: List[Dict[str, Any]] = []
        current_tc: Optional[Dict[str, Any]] = None

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

        # Tool calls: executar e continuar (ordem: assistant -> tool responses)
        msg = {"role": "assistant", "content": full_content or None, "tool_calls": []}
        for tc in tool_calls_buf:
            tid = tc.get("id", "")
            name = tc.get("name", "")
            args_str = tc.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else {}
            except json.JSONDecodeError:
                args = {}
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
        tool_choice = "auto"


def stream_chat_yui_sync(
    mensagem: str,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    system_override: Optional[str] = None,
) -> Generator[str, None, None]:
    """Wrapper síncrono para stream_chat_yui (para uso em Flask/Generator)."""
    q: queue.Queue = queue.Queue()

    def run_async():
        async def consume():
            try:
                async for chunk in stream_chat_yui(mensagem, chat_id, user_id, system_override):
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
