"""
Relatório final de análise: orquestra scanners e formatadores.
SOMENTE LEITURA — NUNCA edita, NUNCA gera patch, NUNCA pede confirmação de edição.
"""

import os
from typing import Dict, Optional, Tuple, Any

from yui_ai.project_analysis.project_scanner import escanear_estrutura, DEFAULT_PROJECT_ROOT
from yui_ai.project_analysis.architecture_analyzer import analisar_arquitetura
from yui_ai.project_analysis.quality_analyzer import analisar_qualidade
from yui_ai.project_analysis.roadmap_generator import gerar_roadmap


def executar_analise_completa(raiz: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Executa análise completa do projeto (somente leitura).

    Retorna (sucesso, dados, erro):
        - sucesso: True apenas após a análise completar corretamente
        - dados: dict com visao_geral, pontos_fortes, pontos_fracos, riscos_tecnicos,
          sugestoes_melhoria, roadmap, scanner, arquitetura, texto_formatado; ou None
        - erro: mensagem de erro ou None
    """
    sucesso = False
    erro = None
    dados = None
    try:
        raiz_abs = os.path.abspath(raiz or DEFAULT_PROJECT_ROOT)
        scanner = escanear_estrutura(raiz_abs)
        arquitetura = analisar_arquitetura(scanner)
        qualidade = analisar_qualidade(scanner, arquitetura)
        roadmap = gerar_roadmap(scanner, arquitetura, qualidade)

        nome_projeto = os.path.basename(raiz_abs) or "Projeto"
        visao_geral = (
            f"Projeto: {nome_projeto}. "
            f"Raiz: {raiz_abs}. "
            f"Total de arquivos: {scanner.get('total_arquivos', 0)}. "
            f"Módulos principais: {', '.join(scanner.get('modulos_principais', []))}."
        )

        sugestoes = []
        sugestoes.extend(qualidade.get("pontos_fracos", []))
        sugestoes.extend(roadmap.get("curto_prazo", [])[:2])

        dados = {
            "visao_geral": visao_geral,
            "pontos_fortes": qualidade.get("pontos_fortes", []),
            "pontos_fracos": qualidade.get("pontos_fracos", []),
            "riscos_tecnicos": qualidade.get("riscos_tecnicos", []),
            "sugestoes_melhoria": sugestoes,
            "roadmap": roadmap,
            "scanner": scanner,
            "arquitetura": arquitetura,
            "texto_formatado": formatar_relatorio({
                "visao_geral": visao_geral,
                "pontos_fortes": qualidade["pontos_fortes"],
                "pontos_fracos": qualidade["pontos_fracos"],
                "riscos_tecnicos": qualidade["riscos_tecnicos"],
                "roadmap": roadmap,
            }),
        }
        sucesso = True
    except Exception as e:
        erro = str(e)
    return sucesso, dados, erro


def formatar_relatorio(dados: Dict) -> str:
    """
    Formata o relatório para exibição (terminal e GUI).
    Cabeçalhos claros, emojis leves (📊 🧠 ⚠️ 🚀).
    """
    linhas = [
        "",
        "=" * 60,
        "  📊 RELATÓRIO DE ANÁLISE DO PROJETO (somente leitura)",
        "=" * 60,
        "",
        "🧠 VISÃO GERAL",
        "-" * 40,
        dados.get("visao_geral", ""),
        "",
        "✅ PONTOS FORTES",
        "-" * 40,
    ]
    for p in dados.get("pontos_fortes", []):
        linhas.append(f"  • {p}")
    linhas.extend([
        "",
        "⚠️ PONTOS FRACOS",
        "-" * 40,
    ])
    for p in dados.get("pontos_fracos", []):
        linhas.append(f"  • {p}")
    linhas.extend([
        "",
        "⚠️ RISCOS TÉCNICOS",
        "-" * 40,
    ])
    for r in dados.get("riscos_tecnicos", []):
        linhas.append(f"  • {r}")
    linhas.extend([
        "",
        "🚀 ROADMAP DE MELHORIAS",
        "-" * 40,
        "  Curto prazo:",
    ])
    for s in dados.get("roadmap", {}).get("curto_prazo", []):
        linhas.append(f"    • {s}")
    linhas.extend([
        "  Médio prazo:",
    ])
    for s in dados.get("roadmap", {}).get("medio_prazo", []):
        linhas.append(f"    • {s}")
    linhas.extend([
        "  Longo prazo:",
    ])
    for s in dados.get("roadmap", {}).get("longo_prazo", []):
        linhas.append(f"    • {s}")
    linhas.extend([
        "",
        "=" * 60,
    ])
    return "\n".join(linhas)
