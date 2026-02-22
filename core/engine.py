"""
Engine central da Yui: processa mensagens com histórico e persiste no Supabase.
"""
import json
import os

from openai import OpenAI

from core.chat_summarizer import summarize_chat
from yui_ai.services.memory_service import load_history as get_messages, save_message
from core.memory_manager import add_event, build_context_text
from core.tool_runner import run_tool
from core.user_profile import get_user_profile
from pathlib import Path

OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Modelo: gpt-4o disponível; gpt-5.2 não existe ainda
MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-5-mini")


def process_message(user_id, chat_id, message):
    # Persiste mensagem no histórico do chat
    save_message(chat_id, "user", message, user_id)

    # Histórico do chat
    history = get_messages(chat_id)
    msgs = [{"role": m["role"], "content": m["content"] or ""} for m in history]

    # Perfil do usuário (personalidade adaptativa)
    profile = get_user_profile(user_id)

    # Protocolo de tool calling via JSON (em português) com PLANNER.
    # Ferramentas disponíveis:
    # - analisar_arquivo(filename, content): analisar um código/arquivo que o usuário colou na mensagem.
    # - listar_arquivos(pasta, padrao, limite): listar arquivos de uma pasta do projeto.
    # - ler_arquivo_texto(caminho, max_chars): ler o conteúdo de um arquivo de texto do projeto.
    # - analisar_projeto(raiz?): analisar arquitetura, riscos e roadmap do projeto.
    # - observar_ambiente(raiz?): fazer uma leitura rápida da estrutura do projeto e sugerir próximos passos.
    # - criar_projeto_arquivos(root_dir, files): criar fisicamente um mini-projeto (pastas/arquivos) com base na estrutura que você definir.
    # - criar_zip_projeto(root_dir, zip_name?): gerar um script Python para compactar o projeto em ZIP (ignorando arquivos sensíveis).
    # - consultar_indice_projeto(raiz?): consultar o índice de arquitetura/riscos/roadmap em cache (sem reprocessar o projeto).
    tool_system = (
        "Você é a Yui, uma IA desenvolvedora que responde SEMPRE em português do Brasil.\n"
        "Você tem acesso a ferramentas internas. Use-as quando isso gerar uma resposta mais útil.\n\n"
        "Ferramentas disponíveis (nomes exatos):\n"
        "- analisar_arquivo(filename, content): quando o usuário COLAR ou descrever um código/arquivo específico para análise.\n"
        "- listar_arquivos(pasta, padrao, limite): quando o usuário pedir para ver arquivos do projeto ou listar pastas.\n"
        "- ler_arquivo_texto(caminho, max_chars): quando o usuário pedir para abrir/ler o conteúdo de um arquivo.\n"
        "- analisar_projeto(raiz?): quando o usuário pedir para analisar a ARQUITETURA completa, riscos técnicos ou roadmap do projeto.\n"
        "- observar_ambiente(raiz?): quando quiser ter uma visão rápida do tipo de projeto aberto e sugestões iniciais.\n"
        "- criar_projeto_arquivos(root_dir, files): quando o usuário pedir para CRIAR um projeto/mini SaaS, você define os arquivos e caminhos e pede para gravar tudo no workspace.\n"
        "- criar_zip_projeto(root_dir, zip_name?): quando o usuário pedir um ZIP do projeto, gere o script de compactação.\n"
        "- consultar_indice_projeto(raiz?): quando quiser consultar rapidamente o índice de arquitetura/riscos/roadmap em cache.\n\n"
        "Planejamento:\n"
        "- Se resolver com texto direto, use:\n"
        '  {"mode":"answer","answer":"sua resposta em português aqui"}\n'
        "- Se precisar de UMA OU MAIS ferramentas, responda SOMENTE um JSON neste formato:\n"
        '  {"mode":"tools","steps":[{"tool":"NOME_DA_FERRAMENTA","args":{...}}, ...], "final_answer":"(opcional) conclusão em texto"}\n'
        "Exemplos de steps:\n"
        '{"tool":"analisar_arquivo","args":{"filename":"main.py","content":"<código aqui>"}}.\n'
        '{"tool":"listar_arquivos","args":{"pasta":"yui_ai","padrao":"*.py","limite":20}}.\n'
        '{"tool":"ler_arquivo_texto","args":{"caminho":"yui_ai/main.py","max_chars":2000}}.\n'
        '{"tool":"analisar_projeto","args":{}}.\n'
        '{"tool":"observar_ambiente","args":{}}.\n'
        '{"tool":"criar_projeto_arquivos","args":{"root_dir":"mini-saas-blog","files":[{"path":"index.html","content":"...html..."},{"path":"static/styles.css","content":"...css..."}]}}.\n'
        '{"tool":"criar_zip_projeto","args":{"root_dir":"generated_projects/mini-saas-blog","zip_name":"mini-saas-blog"}}.\n\n'
        "Quando quiser responder normalmente SEM usar ferramenta, responda SOMENTE um JSON neste formato (sem texto extra fora do JSON):\n"
        '{"mode":"answer","answer":"sua resposta em português aqui"}.\n'
        "NUNCA misture explicações fora do JSON. O JSON deve ser o único conteúdo da resposta."
    )

    # Memória contextual: combina memória curta e longa
    contexto = build_context_text(user_id=user_id, chat_id=chat_id, limit_short=8, limit_long=8)
    if contexto:
        msgs.insert(0, {"role": "system", "content": contexto})

    # Mensagem de sistema com o perfil do usuário
    if profile:
        nivel = profile.get("nivel_tecnico") or "desconhecido"
        langs = profile.get("linguagens_pref") or ""
        modo = profile.get("modo_resposta") or "dev"
        perfil_txt = (
            "Informações sobre o usuário atual para adaptar o TOM da resposta:\n"
            f"- Nível técnico: {nivel} (iniciante/intermediario/avancado).\n"
            f"- Linguagens preferidas: {langs or 'não especificado'}.\n"
            f"- Modo de resposta preferido: {modo} "
            "(dev = direto ao ponto e focado em código; explicativo = mais didático; resumido = respostas menores).\n"
            "Ajuste o nível de detalhe e exemplos com base nesses dados.\n"
        )
        msgs.insert(0, {"role": "system", "content": perfil_txt})

    # Mensagem de sistema com o protocolo de tools
    msgs.insert(0, {"role": "system", "content": tool_system})

    if not client:
        return "⚠️ Configure OPENAI_API_KEY no servidor para respostas da Yui."

    response = client.chat.completions.create(
        model=MODEL,
        messages=msgs,
        temperature=0.6,
        max_tokens=4096,
    )
    raw_content = ""
    if response.choices and len(response.choices) > 0:
        raw_content = (response.choices[0].message.content or "").strip()

    def _parse_json(text: str):
        """Extrai e parseia um JSON de tools/answer mesmo com markdown ou texto ao redor."""
        if not text:
            return None
        s = text.strip()
        # Remove blocos markdown ```json ... ``` ou ``` ... ```
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
        # Encontra o par de chaves raiz (evita cortar em } dentro de strings)
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

    data = _parse_json(raw_content)
    if data is None and ('"mode"' in raw_content or "'mode'" in raw_content) and ("tools" in raw_content or "tool" in raw_content):
        data = _parse_json(raw_content[raw_content.find("{"):] if "{" in raw_content else raw_content)

    def _maybe_summarize(reply_text: str) -> None:
        """
        Aciona um resumo periódico da conversa e grava em memória longa.
        Estratégia simples: a cada ~16 mensagens no histórico.
        """
        try:
            # Considera o histórico atual + a nova resposta
            history_for_summary = list(history) + [
                {"role": "assistant", "content": reply_text or ""}
            ]
            total = len(history_for_summary)
            if total >= 16 and total % 16 == 0:
                # Usa apenas os últimos 16 turnos para o resumo
                recorte = history_for_summary[-16:]
                summarize_chat(user_id=user_id, chat_id=chat_id, messages=recorte)
        except Exception:
            # Memória não deve quebrar o fluxo normal
            return

    # Fallback: modelo não respeitou o contrato, trata como resposta normal
    if not isinstance(data, dict) or "mode" not in data:
        reply = raw_content.strip()
        save_message(chat_id, "assistant", reply, user_id)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
        _maybe_summarize(reply)
        return reply

    mode = data.get("mode")

    # Caso simples: resposta direta
    if mode == "answer":
        reply = str(data.get("answer") or "").strip()
        if not reply:
            reply = raw_content.strip()
        save_message(chat_id, "assistant", reply, user_id)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
        _maybe_summarize(reply)
        return reply

    # Planner escolheu usar ferramentas (uma ou mais)
    if mode in ("tool", "tools"):
        # Compatibilidade com formato antigo: mode == "tool"
        if mode == "tool":
            steps = [{"tool": str(data.get("tool") or "").strip(), "args": data.get("args") or {}}]
        else:
            raw_steps = data.get("steps") or []
            steps = []
            for s in raw_steps:
                if not isinstance(s, dict):
                    continue
                name = str(s.get("tool") or "").strip()
                if not name:
                    continue
                steps.append({"tool": name, "args": s.get("args") or {}})

        if not steps:
            # Sem steps válidos, volta para resposta normal
            reply = raw_content.strip()
            save_message(chat_id, "assistant", reply, user_id)
            add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
            add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
            _maybe_summarize(reply)
            return reply

        partes: list[str] = []

        for step in steps:
            tool_name = step["tool"]
            args = step.get("args") or {}
            result = run_tool(tool_name, args)
            if not result.get("ok"):
                partes.append(
                    f"Não consegui executar a ferramenta '{tool_name}': {result.get('error') or 'erro desconhecido.'}"
                )
                continue

            payload = result.get("result") or {}
            # Respostas específicas por ferramenta
            if tool_name == "analisar_arquivo":
                partes.append(
                    payload.get("text")
                    or "Análise concluída, mas não foi possível obter o texto do relatório."
                )
            elif tool_name == "analisar_projeto":
                partes.append(
                    payload.get("texto")
                    or "Análise de projeto concluída, mas não foi possível obter o texto formatado."
                )
            elif tool_name == "listar_arquivos":
                arquivos = payload.get("arquivos") or []
                if not arquivos:
                    partes.append("Não encontrei arquivos para os critérios informados.")
                else:
                    linhas = ["Arquivos encontrados:"]
                    linhas.extend(f"- {a}" for a in arquivos)
                    partes.append("\n".join(linhas))
            elif tool_name == "ler_arquivo_texto":
                conteudo = payload.get("conteudo") or ""
                caminho = args.get("caminho") or "arquivo"
                if not conteudo:
                    partes.append(f"O arquivo {caminho} está vazio ou não pôde ser lido.")
                else:
                    partes.append(f"Conteúdo de {caminho} (parcial se muito grande):\n\n{conteudo}")
            elif tool_name == "observar_ambiente":
                resumo = payload.get("resumo") or ""
                sugestao = payload.get("sugestao") or ""
                if sugestao:
                    partes.append(resumo + "\n\n" + sugestao)
                else:
                    partes.append(resumo or "Observei o projeto, mas não consegui gerar um resumo útil.")
            elif tool_name == "criar_projeto_arquivos":
                root = payload.get("root") or ""
                files = payload.get("files") or []
                if not payload.get("ok"):
                    partes.append(
                        f"Não consegui criar o projeto: {payload.get('error') or 'erro desconhecido.'}"
                    )
                else:
                    linhas = [
                        "Projeto criado com sucesso.",
                        f"Pasta raiz: {root or 'generated_projects/'}",
                    ]
                    if files:
                        linhas.append("Arquivos criados:")
                        linhas.extend(f"- {p}" for p in files)
                    slug = ""
                    if root:
                        try:
                            slug = Path(root).name
                        except Exception:
                            slug = ""
                    if slug:
                        linhas.append("")
                        linhas.append(f"[PREVIEW_URL]: /generated/{slug}/index.html")
                    partes.append("\n".join(linhas))
            elif tool_name == "criar_zip_projeto":
                if not payload.get("ok"):
                    partes.append(
                        f"Não consegui preparar o ZIP do projeto: {payload.get('error') or 'erro desconhecido.'}"
                    )
                else:
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
                    partes.append("\n".join(linhas))
            else:
                # Fallback genérico: serializa o payload em JSON legível
                partes.append(json.dumps(payload, ensure_ascii=False, indent=2))

        final_answer = str(data.get("final_answer") or "").strip()
        if final_answer:
            partes.append("")
            partes.append(final_answer)

        reply = "\n\n".join(p for p in partes if p)
        if not reply:
            reply = "Execução das ferramentas concluída, mas não consegui gerar uma resposta textual útil."

        save_message(chat_id, "assistant", reply, user_id)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
        _maybe_summarize(reply)
        return reply

    # Modo desconhecido: volta para texto cru
    reply = raw_content.strip()
    save_message(chat_id, "assistant", reply, user_id)
    add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
    add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
    _maybe_summarize(reply)
    return reply
