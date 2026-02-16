"""
Formatação do relatório final de análise de arquivo.
Agrega função, estrutura, problemas e sugestões.
Pipeline: upload -> file_reader -> file_intelligence -> error_detector -> relatório.
"""

from typing import Any, Dict, List, Optional, Tuple

from yui_ai.analyzer.file_reader import read_file_safe
from yui_ai.analyzer.file_intelligence import analyze_file, get_language
from yui_ai.analyzer.error_detector import detect_issues


def run_file_analysis(content: bytes, filename: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Pipeline completo: leitura segura -> inteligência -> detecção de erros -> relatório.
    SEGURANÇA: NUNCA executa o arquivo — somente leitura estática, regex e parser.
    Retorna (sucesso, relatório, erro).
    """
    text, err = read_file_safe(content, filename)
    if err:
        return False, None, err
    language = get_language(filename)
    intelligence = analyze_file(text, language, filename)
    issues = detect_issues(text, language, filename)
    report = build_report(intelligence, issues, filename, language)
    return True, report, None


def build_report(
    intelligence: Dict[str, Any],
    issues: List[Dict[str, Any]],
    filename: str,
    language: str,
) -> Dict[str, Any]:
    """
    Monta o relatório final a partir da inteligência e dos problemas detectados.

    Returns:
        Dict com: funcao, estrutura, problemas, sugestoes, resumo.
    """
    funcao = intelligence.get("funcao", "Não identificada.")
    estrutura_raw = intelligence.get("estrutura", [])
    estrutura_texto = _format_structure(estrutura_raw)

    problemas = []
    sugestoes = []
    for i in issues:
        problemas.append({
            "tipo": i.get("tipo", "aviso"),
            "mensagem": i.get("mensagem", ""),
            "linha": i.get("linha"),
        })
        if i.get("sugestao"):
            sugestoes.append(i["sugestao"])

    # Remove sugestões duplicadas mantendo ordem
    sugestoes_unicas = []
    for s in sugestoes:
        if s not in sugestoes_unicas:
            sugestoes_unicas.append(s)

    resumo = _build_resumo(problemas, sugestoes_unicas, language)

    return {
        "funcao": funcao,
        "estrutura": estrutura_texto,
        "estrutura_raw": estrutura_raw,
        "problemas": problemas,
        "sugestoes": sugestoes_unicas,
        "resumo": resumo,
        "linguagem": language,
        "arquivo": filename,
    }


def _format_structure(estrutura: List[Dict[str, Any]]) -> str:
    """Converte estrutura em texto legível."""
    if not estrutura:
        return "Nenhuma estrutura extraída."
    linhas = []
    for item in estrutura[:50]:  # limita para não ficar gigante
        tipo = item.get("tipo", "?")
        nome = item.get("nome", "")
        if nome:
            linhas.append(f"  • {tipo}: {nome}")
        elif "mensagem" in item:
            linhas.append(f"  • {item['mensagem']}")
        elif "linhas" in item:
            linhas.append(f"  • {tipo}: {item['linhas']} linhas")
        else:
            linhas.append(f"  • {tipo}")
    return "\n".join(linhas) if linhas else "—"


def _build_resumo(problemas: List[Dict], sugestoes: List[str], language: str) -> str:
    """Texto resumido para exibição rápida."""
    n = len(problemas)
    if n == 0:
        return f"Arquivo {language}: nenhum problema detectado. Estrutura analisada com sucesso."
    erros = sum(1 for p in problemas if p.get("tipo") == "erro")
    riscos = sum(1 for p in problemas if p.get("tipo") == "risco")
    return (
        f"Arquivo {language}: {n} ponto(s) encontrado(s) "
        f"({erros} erro(s), {riscos} risco(s)). "
        f"{len(sugestoes)} sugestão(ões) de melhoria."
    )


def report_to_text(report: Dict[str, Any]) -> str:
    """Converte o relatório em texto para exibição na UI."""
    linhas = [
        "",
        "=" * 50,
        "  RELATÓRIO DE ANÁLISE DO ARQUIVO",
        "=" * 50,
        "",
        f"Arquivo: {report.get('arquivo', '—')}",
        f"Linguagem: {report.get('linguagem', '—')}",
        "",
        "FUNÇÃO DO ARQUIVO",
        "-" * 40,
        report.get("funcao", "—"),
        "",
        "ESTRUTURA",
        "-" * 40,
        report.get("estrutura", "—"),
        "",
        "PROBLEMAS ENCONTRADOS",
        "-" * 40,
    ]
    for p in report.get("problemas", []):
        linha = f"  [{p.get('tipo', '?')}] {p.get('mensagem', '')}"
        if p.get("linha"):
            linha += f" (linha {p['linha']})"
        linhas.append(linha)
    if not report.get("problemas"):
        linhas.append("  Nenhum problema detectado.")
    linhas.extend([
        "",
        "SUGESTÕES DE MELHORIA",
        "-" * 40,
    ])
    for s in report.get("sugestoes", []):
        linhas.append(f"  • {s}")
    if not report.get("sugestoes"):
        linhas.append("  Nenhuma sugestão adicional.")
    linhas.extend(["", "=" * 50, ""])
    return "\n".join(linhas)
