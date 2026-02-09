"""
Construtor de relatório técnico: orquestra scanner, dependências, arquitetura e riscos.
SOMENTE LEITURA. NUNCA altera o projeto analisado.
"""

import os
from typing import Any, Dict, Optional, Tuple

from yui_ai.analyzer.project_scanner import scan_structure
from yui_ai.analyzer.dependency_mapper import build_dependency_graph
from yui_ai.analyzer.architecture_analyzer import analyze_architecture
from yui_ai.analyzer.risk_detector import detect_risks


def run_analysis(root: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Executa análise completa do projeto (somente leitura).

    Args:
        root: Caminho da raiz do projeto a analisar.

    Returns:
        (sucesso, dados, erro)
        - dados: visao_geral, pontos_fortes, pontos_fracos, riscos_tecnicos,
          roadmap, scanner, arquitetura, dependencias, texto_formatado
    """
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        return False, None, f"Diretório não encontrado: {root}"

    try:
        scanner = scan_structure(root)
        dependency = build_dependency_graph(root)
        architecture = analyze_architecture(scanner)
        risks = detect_risks(scanner, architecture, dependency)

        nome_projeto = os.path.basename(root) or "Projeto"
        visao_geral = (
            f"Projeto: {nome_projeto}. "
            f"Raiz: {root}. "
            f"Total de arquivos: {scanner.get('total_arquivos', 0)}. "
            f"Módulos principais: {', '.join(scanner.get('modulos_principais', []))}. "
            f"Arquivos Python: {dependency.get('stats', {}).get('total_arquivos_py', 0)}."
        )

        roadmap = _build_roadmap(scanner, architecture, risks)
        texto = format_report(
            visao_geral=visao_geral,
            pontos_fortes=risks["pontos_fortes"],
            pontos_fracos=risks["pontos_fracos"],
            riscos_tecnicos=risks["riscos_tecnicos"],
            ciclos=risks.get("ciclos", []),
            roadmap=roadmap,
            dependency_stats=dependency.get("stats", {}),
        )

        dados = {
            "visao_geral": visao_geral,
            "pontos_fortes": risks["pontos_fortes"],
            "pontos_fracos": risks["pontos_fracos"],
            "riscos_tecnicos": risks["riscos_tecnicos"],
            "ciclos": risks.get("ciclos", []),
            "roadmap": roadmap,
            "scanner": scanner,
            "arquitetura": architecture,
            "dependencias": dependency,
            "riscos": risks,
            "texto_formatado": texto,
        }
        return True, dados, None
    except Exception as e:
        return False, None, str(e)


def _build_roadmap(
    scanner_data: Dict,
    architecture_data: Dict,
    risks_data: Dict,
) -> Dict:
    """Gera sugestões de roadmap curto, médio e longo prazo."""
    modulos = scanner_data.get("modulos_principais", [])
    pontos_fracos = risks_data.get("pontos_fracos", [])
    riscos = risks_data.get("riscos_tecnicos", [])
    ciclos = risks_data.get("ciclos", [])

    curto = [
        "Manter documentação (README) atualizada",
        "Garantir cobertura de testes nos módulos críticos" if "validation" in modulos else "Revisar testes nos módulos críticos",
    ]
    if ciclos:
        curto.append("Resolver dependências circulares identificadas no relatório")

    medio = [
        "Endereçar pontos fracos estruturais identificados" if pontos_fracos else "Manter estrutura atual",
        "Considerar testes de integração para o fluxo principal",
        "Documentar contrato entre camadas (core, actions, analyzer)",
    ]

    longo = [
        "Avaliar modularização adicional se o projeto crescer",
        "Monitorar dependências circulares e acoplamento" if riscos else "Manter acoplamento sob controle",
    ]

    return {"curto_prazo": curto, "medio_prazo": medio, "longo_prazo": longo}


def format_report(
    visao_geral: str,
    pontos_fortes: list,
    pontos_fracos: list,
    riscos_tecnicos: list,
    ciclos: list,
    roadmap: Dict,
    dependency_stats: Optional[Dict] = None,
) -> str:
    """Formata o relatório para exibição no terminal."""
    dep = dependency_stats or {}
    linhas = [
        "",
        "=" * 60,
        "  RELATÓRIO DE ANÁLISE DO PROJETO (somente leitura)",
        "=" * 60,
        "",
        "VISÃO GERAL",
        "-" * 40,
        visao_geral,
        "",
        "ESTATÍSTICAS DE DEPENDÊNCIAS",
        "-" * 40,
        f"  Arquivos Python analisados: {dep.get('total_arquivos_py', 0)}",
        f"  Arestas (imports internos): {dep.get('total_arestas', 0)}",
        f"  Ciclos detectados: {dep.get('ciclos', 0)}",
        "",
        "PONTOS FORTES",
        "-" * 40,
    ]
    for p in pontos_fortes:
        linhas.append(f"  • {p}")
    linhas.extend([
        "",
        "PONTOS FRACOS",
        "-" * 40,
    ])
    for p in pontos_fracos:
        linhas.append(f"  • {p}")
    linhas.extend([
        "",
        "RISCOS TÉCNICOS",
        "-" * 40,
    ])
    for r in riscos_tecnicos:
        linhas.append(f"  • {r}")
    if ciclos:
        linhas.extend([
            "",
            "CICLOS DE DEPENDÊNCIA",
            "-" * 40,
        ])
        for c in ciclos:
            linhas.append(f"  • {' → '.join(c)}")
    linhas.extend([
        "",
        "ROADMAP DE MELHORIAS",
        "-" * 40,
        "  Curto prazo:",
    ])
    for s in roadmap.get("curto_prazo", []):
        linhas.append(f"    • {s}")
    linhas.extend(["  Médio prazo:"])
    for s in roadmap.get("medio_prazo", []):
        linhas.append(f"    • {s}")
    linhas.extend(["  Longo prazo:"])
    for s in roadmap.get("longo_prazo", []):
        linhas.append(f"    • {s}")
    linhas.extend([
        "",
        "=" * 60,
    ])
    return "\n".join(linhas)
