"""
Engine central da Yui: processa mensagens com histórico e persiste no Supabase.
"""
import json
import os

from openai import OpenAI

from core.memory import get_messages, save_message
from core.memory_events import registrar_evento, buscar_eventos
from core.tool_runner import run_tool
from core.user_profile import get_user_profile
from pathlib import Path

OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Modelo: gpt-4o disponível; gpt-5.2 não existe ainda
MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def process_message(user_id, chat_id, message):
    # Persiste mensagem no histórico do chat
    save_message(chat_id, "user", message)

    # Histórico do chat
    history = get_messages(chat_id)
    msgs = [{"role": m["role"], "content": m["content"] or ""} for m in history]

    # Perfil do usuário (personalidade adaptativa)
    profile = get_user_profile(user_id)

    # Protocolo de tool calling via JSON (em português).
    # Ferramentas disponíveis:
    # - analisar_arquivo(filename, content): analisar um código/arquivo que o usuário colou na mensagem.
    # - listar_arquivos(pasta, padrao, limite): listar arquivos de uma pasta do projeto.
    # - ler_arquivo_texto(caminho, max_chars): ler o conteúdo de um arquivo de texto do projeto.
    # - analisar_projeto(raiz?): analisar arquitetura, riscos e roadmap do projeto.
    # - observar_ambiente(raiz?): fazer uma leitura rápida da estrutura do projeto e sugerir próximos passos.
    # - criar_projeto_arquivos(root_dir, files): criar fisicamente um mini-projeto (pastas/arquivos) com base na estrutura que você definir.
    # - criar_zip_projeto(root_dir, zip_name?): gerar um script Python para compactar o projeto em ZIP (ignorando arquivos sensíveis).
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
        "- criar_zip_projeto(root_dir, zip_name?): quando o usuário pedir um ZIP do projeto, gere o script de compactação.\n\n"
        "QUANDO quiser usar uma ferramenta, responda SOMENTE um JSON, sem nenhum texto extra, exatamente neste formato:\n"
        '{"mode":"tool","tool":"NOME_DA_FERRAMENTA","args":{...}}.\n'
        "Exemplos:\n"
        '{"mode":"tool","tool":"analisar_arquivo","args":{"filename":"main.py","content":"<código aqui>"}}.\n'
        '{"mode":"tool","tool":"listar_arquivos","args":{"pasta":"yui_ai","padrao":"*.py","limite":20}}.\n'
        '{"mode":"tool","tool":"ler_arquivo_texto","args":{"caminho":"yui_ai/main.py","max_chars":2000}}.\n'
        '{"mode":"tool","tool":"analisar_projeto","args":{}}.\n'
        '{"mode":"tool","tool":"observar_ambiente","args":{}}.\n'
        '{"mode":"tool","tool":"criar_projeto_arquivos","args":{"root_dir":"mini-saas-blog","files":[{"path":"index.html","content":"...html..."},{"path":"static/styles.css","content":"...css..."}]}}.\n'
        '{"mode":"tool","tool":"criar_zip_projeto","args":{"root_dir":"generated_projects/mini-saas-blog","zip_name":"mini-saas-blog"}}.\n\n'
        "Quando quiser responder normalmente SEM usar ferramenta, responda SOMENTE um JSON neste formato:\n"
        '{"mode":"answer","answer":"sua resposta em português aqui"}.\n'
        "NUNCA misture explicações fora do JSON. O JSON deve ser o único conteúdo da resposta."
    )

    # Memória contextual: eventos recentes (curta/longa/tecnica)
    eventos = buscar_eventos(user_id=user_id, chat_id=None, tipo=None, limit=10)
    if eventos:
        resumo_memoria = "Fatos importantes e contexto recente deste usuário:\n"
        for ev in reversed(eventos):
            resumo_memoria += f"- ({ev.get('tipo', 'curta')}) {ev.get('conteudo', '')}\n"
        msgs.insert(0, {"role": "system", "content": resumo_memoria})

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

    response = client.chat.completions.create(model=MODEL, messages=msgs)
    raw_content = response.choices[0].message.content or ""

    def _parse_json(text: str):
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("JSON não encontrado")
            return json.loads(text[start : end + 1])
        except Exception:
            return None

    data = _parse_json(raw_content)

    # Fallback: modelo não respeitou o contrato, trata como resposta normal
    if not isinstance(data, dict) or "mode" not in data:
        reply = raw_content.strip()
        save_message(chat_id, "assistant", reply)
        registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
        registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
        return reply

    mode = data.get("mode")

    # Caso simples: resposta direta
    if mode == "answer":
        reply = str(data.get("answer") or "").strip()
        if not reply:
            reply = raw_content.strip()
        save_message(chat_id, "assistant", reply)
        registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
        registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
        return reply

    # Chamada de ferramenta
    if mode == "tool":
        tool_name = str(data.get("tool") or "").strip()
        args = data.get("args") or {}
        if not tool_name:
            # Sem ferramenta válida, volta para resposta normal
            reply = raw_content.strip()
            save_message(chat_id, "assistant", reply)
            registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
            registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
            return reply

        result = run_tool(tool_name, args)
        if not result.get("ok"):
            reply = f"Não consegui executar a ferramenta '{tool_name}': {result.get('error') or 'erro desconhecido.'}"
        else:
            payload = result.get("result") or {}
            # Respostas específicas por ferramenta
            if tool_name == "analisar_arquivo":
                reply = payload.get("text") or "Análise concluída, mas não foi possível obter o texto do relatório."
            elif tool_name == "analisar_projeto":
                reply = payload.get("texto") or "Análise de projeto concluída, mas não foi possível obter o texto formatado."
            elif tool_name == "listar_arquivos":
                arquivos = payload.get("arquivos") or []
                if not arquivos:
                    reply = "Não encontrei arquivos para os critérios informados."
                else:
                    linhas = ["Arquivos encontrados:"]
                    linhas.extend(f"- {a}" for a in arquivos)
                    reply = "\n".join(linhas)
            elif tool_name == "ler_arquivo_texto":
                conteudo = payload.get("conteudo") or ""
                caminho = args.get("caminho") or "arquivo"
                if not conteudo:
                    reply = f"O arquivo {caminho} está vazio ou não pôde ser lido."
                else:
                    reply = f"Conteúdo de {caminho} (parcial se muito grande):\n\n{conteudo}"
            elif tool_name == "observar_ambiente":
                resumo = payload.get("resumo") or ""
                sugestao = payload.get("sugestao") or ""
                if sugestao:
                    reply = resumo + "\n\n" + sugestao
                else:
                    reply = resumo or "Observei o projeto, mas não consegui gerar um resumo útil."
            elif tool_name == "criar_projeto_arquivos":
                root = payload.get("root") or ""
                files = payload.get("files") or []
                if not payload.get("ok"):
                    reply = f"Não consegui criar o projeto: {payload.get('error') or 'erro desconhecido.'}"
                else:
                    linhas = [
                        "Projeto criado com sucesso.",
                        f"Pasta raiz: {root or 'generated_projects/'}",
                    ]
                    if files:
                        linhas.append("Arquivos criados:")
                        linhas.extend(f"- {p}" for p in files)
                    # Se tivermos uma pasta raiz válida, sugere URL de preview
                    slug = ""
                    if root:
                        try:
                            slug = Path(root).name
                        except Exception:
                            slug = ""
                    if slug:
                        linhas.append("")
                        linhas.append(f"[PREVIEW_URL]: /generated/{slug}/index.html")
                    reply = "\n".join(linhas)
            elif tool_name == "criar_zip_projeto":
                if not payload.get("ok"):
                    reply = f"Não consegui preparar o ZIP do projeto: {payload.get('error') or 'erro desconhecido.'}"
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
                    reply = "\n".join(linhas)
            else:
                # Fallback genérico: serializa o payload em JSON legível
                reply = json.dumps(payload, ensure_ascii=False, indent=2)

        save_message(chat_id, "assistant", reply)
        registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
        registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
        return reply

    # Modo desconhecido: volta para texto cru
    reply = raw_content.strip()
    save_message(chat_id, "assistant", reply)
    registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=message)
    registrar_evento(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
    return reply
