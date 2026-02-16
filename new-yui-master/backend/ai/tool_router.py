# ==========================================================
# YUI TOOL ROUTER
# Intercepta respostas da IA, detecta quando é ação (tool)
# e executa em silêncio; devolve só texto limpo pro usuário.
# ==========================================================

import json
from pathlib import Path
from typing import Any, Dict, List

from core.tool_runner import run_tool


# ==========================================================
# DETECTAR BLOCO JSON DE TOOL
# ==========================================================

def extrair_tool(texto: str) -> Dict[str, Any] | None:
    """
    Procura dentro da resposta da IA um JSON válido
    que represente uma tool/action (mode + steps ou tool/args).
    """
    if not texto or "mode" not in texto:
        return None
    start = texto.find("{")
    if start == -1:
        return None
    # Encontra o par de chaves raiz
    depth = 0
    in_string = None
    escape = False
    for i in range(start, len(texto)):
        c = texto[i]
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
                try:
                    data = json.loads(texto[start : i + 1])
                    if isinstance(data, dict) and "mode" in data:
                        return data
                except Exception:
                    pass
                return None
    return None


def _format_tool_result(tool_name: str, args: Dict, payload: Dict) -> str:
    """Formata resultado de uma tool para mensagem limpa (resumo)."""
    if tool_name == "criar_projeto_arquivos" and payload.get("ok"):
        root = payload.get("root") or ""
        slug = Path(root).name if root else ""
        if slug:
            return f"Projeto criado. [PREVIEW_URL]: /generated/{slug}/index.html"
        return "Projeto criado com sucesso."
    if tool_name == "analisar_arquivo":
        return (payload.get("text") or "Análise concluída.")[:500]
    if tool_name == "analisar_projeto":
        return payload.get("texto") or "Análise de projeto concluída."
    if tool_name == "criar_zip_projeto" and payload.get("ok"):
        zip_output = payload.get("zip_output") or ""
        zip_basename = Path(zip_output).name if zip_output else ""
        if zip_basename and zip_basename.endswith(".zip"):
            pend = " (gerando em background)" if payload.get("zip_pending") else ""
            return f"Projeto compactado{pend}. [DOWNLOAD]:/download/{zip_basename}"
        return "Script de compactação criado. Execute o comando indicado no terminal."
    if tool_name == "listar_arquivos":
        arquivos = payload.get("arquivos") or []
        return f"Arquivos encontrados: {len(arquivos)} itens."
    if tool_name == "ler_arquivo_texto":
        return "Conteúdo do arquivo carregado."
    if tool_name == "observar_ambiente":
        return payload.get("resumo") or "Ambiente observado."
    if tool_name == "create_mission" and payload.get("ok"):
        m = payload.get("mission") or {}
        return f"✨ Missão criada: {m.get('project', '')} — {m.get('goal', '')}"
    if tool_name == "update_mission_progress" and payload.get("ok"):
        return "Progresso da missão atualizado."
    return "Ação executada."


# ==========================================================
# PROCESSAR RESPOSTA DA IA
# ==========================================================

def processar_resposta_ai(texto: str) -> str:
    """
    Se a IA devolveu um JSON de ação (mode/tools ou mode/tool),
    executa as tools e retorna mensagem limpa.
    Caso contrário, devolve o texto original.
    """
    tool_data = extrair_tool(texto)

    if not tool_data:
        return texto

    try:
        # steps (mode "tools") ou um único step (mode "tool")
        steps: List[Dict] = []
        if tool_data.get("mode") == "tool":
            name = (tool_data.get("tool") or "").strip()
            if name:
                steps = [{"tool": name, "args": tool_data.get("args") or {}}]
        else:
            raw = tool_data.get("steps") or tool_data.get("tools") or []
            for s in raw:
                if isinstance(s, dict) and s.get("tool"):
                    steps.append({"tool": str(s["tool"]).strip(), "args": s.get("args") or {}})

        if not steps:
            return texto

        resultados: List[str] = []
        for step in steps:
            tool_nome = step.get("tool")
            args = step.get("args") or {}
            if not tool_nome:
                continue
            result = run_tool(tool_nome, args)
            if result.get("ok"):
                payload = result.get("result") or {}
                resultados.append(_format_tool_result(tool_nome, args, payload))
            else:
                resultados.append(f"Não foi possível executar '{tool_nome}'.")

        final = tool_data.get("final_answer") or tool_data.get("answer")
        if final:
            return (final.strip() + "\n\n" + "\n".join(resultados)).strip()
        if resultados:
            return "\n\n".join(resultados)
        return "✅ Ação executada."
    except Exception as e:
        print("Erro Tool Router:", e)
        return "⚠️ Não consegui executar a ação solicitada."
