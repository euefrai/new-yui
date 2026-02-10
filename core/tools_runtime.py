"""
Implementações das ferramentas (tools) executáveis pela Yui.

Estas funções são registradas em core.tools_registry.
"""

from typing import Any, Dict, Optional, Tuple

from yui_ai.analyzer.report_formatter import run_file_analysis, report_to_text
from yui_ai.project_analysis.analysis_report import executar_analise_completa
from yui_ai.project_analysis.project_scanner import escanear_estrutura


def tool_analisar_arquivo(filename: str, content: str) -> Dict[str, Any]:
    """
    Analisa um arquivo usando o pipeline existente da Yui.

    Args:
        filename: nome do arquivo (ex: main.py)
        content: conteúdo completo do arquivo em texto

    Returns:
        dict com { ok: bool, report: dict|None, text: str, error: str|None }
    """
    if not filename:
        return {"ok": False, "report": None, "text": "", "error": "filename obrigatório"}
    if content is None:
        return {"ok": False, "report": None, "text": "", "error": "content obrigatório"}

    try:
        ok, report, err = run_file_analysis(content.encode("utf-8", errors="ignore"), filename)
        if not ok or not report:
            return {"ok": False, "report": None, "text": "", "error": err or "Falha na análise do arquivo."}
        text = report_to_text(report)
        return {"ok": True, "report": report, "text": text, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "report": None, "text": "", "error": str(e)}


def tool_analisar_projeto(raiz: Optional[str] = None) -> Dict[str, Any]:
    """
    Executa uma análise arquitetural completa do projeto (somente leitura).

    Args:
        raiz: caminho raiz do projeto; se None, usa DEFAULT_PROJECT_ROOT interno.

    Returns:
        dict com { ok: bool, dados: dict|None, texto: str, error: str|None }
    """
    try:
        ok, dados, err = executar_analise_completa(raiz)
        if not ok or not dados:
            return {"ok": False, "dados": None, "texto": "", "error": err or "Falha na análise do projeto."}
        texto = dados.get("texto_formatado") or ""
        return {"ok": True, "dados": dados, "texto": texto, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "dados": None, "texto": "", "error": str(e)}


def tool_observar_ambiente(raiz: Optional[str] = None) -> Dict[str, Any]:
    """
    Observador de ambiente: faz uma leitura rápida da estrutura do projeto
    e gera um pequeno resumo com frameworks/projeto detectados.
    """
    try:
        scanner = escanear_estrutura(raiz)
        raiz_real = scanner.get("raiz", "")
        modulos = scanner.get("modulos_principais", [])
        extensoes = scanner.get("extensoes", {})
        total = scanner.get("total_arquivos", 0)

        linguagens = []
        if ".py" in extensoes:
            linguagens.append("Python")
        if ".js" in extensoes or ".ts" in extensoes:
            linguagens.append("JavaScript/TypeScript")
        if ".html" in extensoes:
            linguagens.append("HTML")
        if ".css" in extensoes:
            linguagens.append("CSS")

        frameworks = []
        if "web_server.py" in (scanner.get("arquivos_por_pasta", {}).get("[raiz]", []) or []):
            frameworks.append("Flask (web_server.py)")
        if "yui_ai" in modulos:
            frameworks.append("Pacote Yui AI (assistente autônoma)")

        resumo = f"Raiz do projeto: {raiz_real or 'desconhecida'}. Total de arquivos: {total}."
        if linguagens:
            resumo += f" Linguagens principais: {', '.join(linguagens)}."
        if modulos:
            resumo += f" Módulos principais: {', '.join(modulos)}."
        sugestao = ""
        if frameworks:
            sugestao = (
                "Detectei estes componentes/frameworks: "
                + ", ".join(frameworks)
                + ". Você pode pedir: 'analisa a arquitetura do projeto' para um relatório completo."
            )

        return {
            "ok": True,
            "resumo": resumo,
            "frameworks": frameworks,
            "linguagens": linguagens,
            "sugestao": sugestao,
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "resumo": "", "frameworks": [], "linguagens": [], "sugestao": "", "error": str(e)}

