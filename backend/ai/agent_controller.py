# ==========================================================
# YUI - AGENT CONTROLLER
# Cérebro central da IA: só ele conversa com a IA, decide
# tools, memória e resposta final. O frontend nunca recebe JSON cru.
# ==========================================================

import json
import os
from pathlib import Path
from typing import Any, Dict, Generator, List

from openai import OpenAI

from core.memory import save_message
from core.memory_manager import add_event
from core.tool_runner import run_tool
from core.user_profile import get_user_profile

from backend.ai.auto_debug import auto_debug
from backend.ai.context_engine import montar_contexto_ia
from backend.ai.context_memory import salvar_memoria as salvar_memoria_chat
from backend.ai.self_reflect import avaliar_resposta
from backend.ai.skill_manager import executar_skill, listar_skills
from backend.ai.task_planner import criar_plano
from backend.ai.tool_router import processar_resposta_ai

# ==========================================================
# CONFIG
# ==========================================================

OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
MAX_HISTORY = 15
CHUNK_SIZE = 50  # tamanho do chunk ao “streamar” a resposta final

TOOL_SYSTEM = (
    "Você é a Yui, uma IA desenvolvedora que responde SEMPRE em português do Brasil.\n"
    "Você tem acesso a ferramentas internas. Use-as quando isso gerar uma resposta mais útil.\n\n"
    "Ferramentas disponíveis (nomes exatos):\n"
    "- analisar_arquivo(filename, content): quando o usuário COLAR ou descrever um código/arquivo específico.\n"
    "- listar_arquivos(pasta, padrao, limite): listar arquivos do projeto.\n"
    "- ler_arquivo_texto(caminho, max_chars): ler conteúdo de um arquivo.\n"
    "- analisar_projeto(raiz?): analisar arquitetura, riscos e roadmap.\n"
    "- observar_ambiente(raiz?): visão rápida do projeto e sugestões.\n"
    "- criar_projeto_arquivos(root_dir, files): criar projeto/mini SaaS (pastas/arquivos).\n"
    "- criar_zip_projeto(root_dir, zip_name?): gerar script para compactar o projeto em ZIP.\n"
    "- consultar_indice_projeto(raiz?): consultar índice de arquitetura em cache.\n\n"
    "Planejamento:\n"
    "- Se resolver com texto direto, responda SOMENTE um JSON:\n"
    '  {"mode":"answer","answer":"sua resposta em português aqui"}\n'
    "- Se precisar de ferramentas, responda SOMENTE um JSON:\n"
    '  {"mode":"tools","steps":[{"tool":"NOME","args":{...}}, ...], "final_answer":"(opcional) conclusão"}\n'
    "NUNCA misture texto fora do JSON. O JSON deve ser o único conteúdo da resposta."
)

# Bloco de SKILLS (habilidades dinâmicas) — montado em tempo de execução
def _build_skills_system() -> str:
    skills = listar_skills()
    if not skills:
        return ""
    lista = "\n".join(f"- {k}: {v.get('descricao', '')}" for k, v in skills.items())
    return (
        "\n\nVocê também possui SKILLS (habilidades dinâmicas). Use quando a tarefa se encaixar.\n"
        f"SKILLS DISPONÍVEIS:\n{lista}\n\n"
        "Para usar uma skill, responda SOMENTE este JSON:\n"
        '{"usar_skill": "nome_da_skill", "dados": { ... }}\n'
        "Os dados dependem da skill (ex: calculadora usa a, b, op)."
    )


def _parse_json(text: str) -> Dict[str, Any] | None:
    """Extrai e parseia um JSON de tools/answer mesmo com markdown ou texto ao redor."""
    if not text:
        return None
    s = text.strip()
    for marker in ("```json", "```"):
        if marker in s:
            i = s.find(marker)
            s = s[i + len(marker) :].strip()
            if s.endswith("```"):
                s = s[: s.rfind("```")].strip()
            break
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = None
    escape = False
    end = -1
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if c == in_string:
                in_string = None
            continue
        if c in ('"', "'"):
            in_string = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        end = s.rfind("}")
    if end == -1 or end < start:
        return None
    try:
        return json.loads(s[start : end + 1])
    except Exception:
        return None


def _format_tool_reply(tool_name: str, args: Dict, payload: Dict) -> str:
    """Formata o resultado de uma tool para texto amigável (igual ao engine)."""
    if tool_name == "analisar_arquivo":
        return payload.get("text") or "Análise concluída, mas não foi possível obter o texto do relatório."
    if tool_name == "analisar_projeto":
        return payload.get("texto") or "Análise de projeto concluída, mas não foi possível obter o texto formatado."
    if tool_name == "listar_arquivos":
        arquivos = payload.get("arquivos") or []
        if not arquivos:
            return "Não encontrei arquivos para os critérios informados."
        linhas = ["Arquivos encontrados:"] + [f"- {a}" for a in arquivos]
        return "\n".join(linhas)
    if tool_name == "ler_arquivo_texto":
        conteudo = payload.get("conteudo") or ""
        caminho = args.get("caminho") or "arquivo"
        if not conteudo:
            return f"O arquivo {caminho} está vazio ou não pôde ser lido."
        return f"Conteúdo de {caminho} (parcial se muito grande):\n\n{conteudo}"
    if tool_name == "observar_ambiente":
        resumo = payload.get("resumo") or ""
        sugestao = payload.get("sugestao") or ""
        return (resumo + "\n\n" + sugestao) if sugestao else (resumo or "Observei o projeto, mas não consegui gerar um resumo útil.")
    if tool_name == "criar_projeto_arquivos":
        root = payload.get("root") or ""
        files = payload.get("files") or []
        if not payload.get("ok"):
            return f"Não consegui criar o projeto: {payload.get('error') or 'erro desconhecido.'}"
        linhas = ["Projeto criado com sucesso.", f"Pasta raiz: {root or 'generated_projects/'}"]
        if files:
            linhas.append("Arquivos criados:")
            linhas.extend(f"- {p}" for p in files)
        try:
            slug = Path(root).name if root else ""
        except Exception:
            slug = ""
        if slug:
            linhas.append("")
            linhas.append(f"[PREVIEW_URL]: /generated/{slug}/index.html")
        return "\n".join(linhas)
    if tool_name == "criar_zip_projeto":
        if not payload.get("ok"):
            return f"Não consegui preparar o ZIP do projeto: {payload.get('error') or 'erro desconhecido.'}"
        script_path = payload.get("script_path") or ""
        zip_output = payload.get("zip_output") or ""
        command = payload.get("command") or ""
        linhas = [
            "Script de compactação criado com sucesso.",
            f"Script: {script_path}",
            f"ZIP de saída (após executar): {zip_output or 'definido no script'}",
        ]
        if command:
            linhas.append(f"Para gerar o ZIP, execute no terminal:\n{command}")
        return "\n".join(linhas)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _yield_in_chunks(text: str, chunk_size: int = CHUNK_SIZE) -> Generator[str, None, None]:
    """Simula streaming entregando o texto em pedaços."""
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


# ==========================================================
# FUNÇÃO PRINCIPAL DO AGENTE (gerador: yield = chunk para o frontend)
# ==========================================================


def agent_controller(
    user_id: str,
    chat_id: str,
    user_message: str,
) -> Generator[str, None, None]:
    """
    Fluxo central da YUI.

    1) Busca memória e contexto
    2) Chama a IA uma vez (resposta em JSON: mode answer ou tools)
    3) Se tools → executa e monta texto da resposta
    4) Entrega a resposta final em chunks (streaming)
    5) Salva memória

    O frontend só recebe texto; nunca JSON cru.
    """
    try:
        # ---------- 1) Context Engine: histórico + contexto do projeto + memórias ----------
        ctx = montar_contexto_ia(user_id, chat_id, user_message, raiz_projeto=".", max_mensagens=MAX_HISTORY)
        msgs: List[Dict[str, str]] = list(ctx.get("historico") or [])

        if ctx.get("contexto_projeto"):
            msgs.insert(0, {
                "role": "system",
                "content": (
                    "Você é a YUI, uma IA desenvolvedora. Use o contexto do projeto abaixo para responder "
                    "de forma compatível com o código existente.\n\n" + ctx["contexto_projeto"]
                )
            })
        if ctx.get("memoria_vetorial"):
            msgs.insert(0, {
                "role": "system",
                "content": (
                    "Você é a YUI, uma IA desenvolvedora especialista. Use o contexto recuperado da memória do projeto:\n"
                    + ctx["memoria_vetorial"]
                )
            })
        if ctx.get("contexto_chat_anterior"):
            msgs.insert(0, {
                "role": "system",
                "content": f"Contexto anterior relevante gerado pela própria Yui:\n\n{ctx['contexto_chat_anterior']}",
            })
        if ctx.get("memoria_eventos"):
            msgs.insert(0, {"role": "system", "content": ctx["memoria_eventos"]})

        profile = get_user_profile(user_id)
        if profile:
            nivel = profile.get("nivel_tecnico") or "desconhecido"
            langs = profile.get("linguagens_pref") or ""
            modo = profile.get("modo_resposta") or "dev"
            perfil_txt = (
                f"Usuário: nível {nivel}, linguagens {langs or 'não especificado'}, modo {modo}. "
                "Ajuste o tom da resposta."
            )
            msgs.insert(0, {"role": "system", "content": perfil_txt})

        skills_system = _build_skills_system()
        msgs.insert(0, {"role": "system", "content": TOOL_SYSTEM + skills_system})
        msgs.append({"role": "user", "content": user_message})

        # ---------- Task Planner: plano interno antes da resposta ----------
        try:
            plano_execucao = criar_plano(user_message)
            if plano_execucao and plano_execucao.strip():
                msgs.insert(0, {"role": "system", "content": plano_execucao.strip()})
        except Exception:
            pass

        if not client:
            for c in _yield_in_chunks("⚠️ Configure OPENAI_API_KEY no servidor para respostas da Yui."):
                yield c
            return

        # ---------- 2) Uma chamada à IA (resposta estruturada) ----------
        response = client.chat.completions.create(model=MODEL, messages=msgs)
        raw_content = (response.choices[0].message.content or "").strip()
        data = _parse_json(raw_content)
        if data is None and ("mode" in raw_content and ("tools" in raw_content or "tool" in raw_content)):
            data = _parse_json(raw_content[raw_content.find("{"):] if "{" in raw_content else raw_content)
        if data is None and "usar_skill" in (raw_content or ""):
            data = _parse_json(raw_content[raw_content.find("{"):] if "{" in raw_content else raw_content)

        # ---------- 3a) Se for skill → executar e usar resultado como resposta ----------
        reply = ""
        if isinstance(data, dict) and data.get("usar_skill"):
            nome_skill = str(data.get("usar_skill") or "").strip()
            dados_skill = data.get("dados") if isinstance(data.get("dados"), dict) else {}
            sucesso, resultado = executar_skill(nome_skill, dados_skill)
            if sucesso:
                reply = json.dumps(resultado, ensure_ascii=False, indent=2) if isinstance(resultado, dict) else str(resultado)
            else:
                reply = f"Não foi possível executar a skill '{nome_skill}': {resultado}"

        # ---------- 3b) Se for tool → executar e montar resposta ----------
        elif isinstance(data, dict) and data.get("mode") in ("tool", "tools"):
            steps: List[Dict] = []
            if data.get("mode") == "tool":
                steps = [{"tool": str(data.get("tool") or "").strip(), "args": data.get("args") or {}}]
            else:
                for s in data.get("steps") or []:
                    if isinstance(s, dict) and s.get("tool"):
                        steps.append({"tool": str(s["tool"]).strip(), "args": s.get("args") or {}})

            partes: List[str] = []
            for step in steps:
                tool_name = step["tool"]
                args = step.get("args") or {}
                result = run_tool(tool_name, args)
                if not result.get("ok"):
                    partes.append(f"Não consegui executar '{tool_name}': {result.get('error') or 'erro desconhecido.'}")
                    continue
                payload = result.get("result") or {}
                partes.append(_format_tool_reply(tool_name, args, payload))

            final_answer = str(data.get("final_answer") or "").strip()
            if final_answer:
                partes.append("")
                partes.append(final_answer)
            reply = "\n\n".join(p for p in partes if p) if partes else "Execução das ferramentas concluída."

        elif isinstance(data, dict) and data.get("mode") == "answer":
            reply = str(data.get("answer") or "").strip() or raw_content.strip()

        else:
            reply = raw_content.strip()

        # ---------- 3c) Self-Reflect + Auto Debug: melhora e corrige erros técnicos ----------
        if client and reply:
            try:
                def _call_model_reflect(messages):
                    r = client.chat.completions.create(model=MODEL, messages=messages)
                    return (r.choices[0].message.content or "").strip()

                melhorou, nova_resposta = avaliar_resposta(_call_model_reflect, msgs, reply)
                if melhorou and nova_resposta:
                    reply = nova_resposta

                corrigiu, resposta_debugada = auto_debug(_call_model_reflect, reply)
                if corrigiu and resposta_debugada:
                    reply = resposta_debugada
            except Exception:
                pass

        # ---------- 4) Tool Router: intercepta JSON de tool e devolve texto limpo ----------
        reply = processar_resposta_ai(reply)

        # ---------- 4b) Salva resposta na memória contextual do chat ----------
        try:
            salvar_memoria_chat(chat_id, reply)
        except Exception:
            pass

        # ---------- 5) Entregar resposta em chunks (streaming) ----------
        for chunk in _yield_in_chunks(reply):
            yield chunk

        # ---------- 6) Salvar memória ----------
        save_message(chat_id, "user", user_message, user_id)
        save_message(chat_id, "assistant", reply, user_id)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=user_message)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)

    except Exception as e:
        erro = f"Erro no Agent Controller: {str(e)}"
        print(erro)
        for c in _yield_in_chunks("⚠️ Algo deu errado ao processar sua mensagem."):
            yield c
