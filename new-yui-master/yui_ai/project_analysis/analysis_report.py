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
from yui_ai.project_analysis.code_quality_metrics import extrair_metricas_python, calcular_score_qualidade
from yui_ai.system.logger import log_event, log_error
from yui_ai.system.history import salvar_historico
from yui_ai.config.config import modo_resposta


def executar_analise_completa(raiz: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Executa análise completa do projeto (somente leitura).

    Retorna (sucesso, dados, erro):
        - sucesso: True apenas após a análise completar corretamente
        - dados: dict com visao_geral, pontos_fortes, pontos_fracos, riscos_tecnicos,
          sugestoes_melhoria, roadmap, scanner, arquitetura, score_qualidade,
          metricas_codigo, problemas_detectados, texto_formatado; ou None
        - erro: mensagem de erro ou None
    """
    sucesso = False
    erro = None
    dados = None
    try:
        log_event("Iniciando análise completa", {"raiz": raiz})
        raiz_abs = os.path.abspath(raiz or DEFAULT_PROJECT_ROOT)
        scanner = escanear_estrutura(raiz_abs)
        arquitetura = analisar_arquitetura(scanner)
        qualidade = analisar_qualidade(scanner, arquitetura)
        roadmap = gerar_roadmap(scanner, arquitetura, qualidade)

        metricas_codigo, problemas_detectados = extrair_metricas_python(raiz_abs)
        dados_intermed = {
            "scanner": scanner,
            "arquitetura": arquitetura,
            "qualidade": qualidade,
            "roadmap": roadmap,
            "metricas_codigo": metricas_codigo,
            "problemas_detectados": problemas_detectados,
        }
        score_qualidade = calcular_score_qualidade(dados_intermed)

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
            "score_qualidade": score_qualidade,
            "metricas_codigo": metricas_codigo,
            "problemas_detectados": problemas_detectados,
            "texto_formatado": formatar_relatorio({
                "visao_geral": visao_geral,
                "pontos_fortes": qualidade["pontos_fortes"],
                "pontos_fracos": qualidade["pontos_fracos"],
                "riscos_tecnicos": qualidade["riscos_tecnicos"],
                "roadmap": roadmap,
                "score_qualidade": score_qualidade,
                "problemas_detectados": problemas_detectados,
            }),
        }
        sucesso = True
        log_event("Análise concluída com sucesso", {"projeto": nome_projeto})
        salvar_historico(
            nome_projeto,
            score_qualidade.get("nota", 0),
            len(problemas_detectados) + len(qualidade.get("pontos_fracos", [])),
        )
    except Exception as e:
        erro = str(e)
        log_error(e, {"contexto": "executar_analise_completa", "raiz": raiz})
    return sucesso, dados, erro


def formatar_relatorio(dados: Dict) -> str:
    """
    Formata o relatório profissional: header, score, classificação, resumo natural,
    visão geral, pontos positivos, problemas (com tags), sugestões.
    Respeita modo_resposta (leigo/avancado).
    """
    score = dados.get("score_qualidade") or {}
    nota = score.get("nota", 0)
    classificacao = score.get("classificacao", "—")
    problemas_detectados = dados.get("problemas_detectados") or []
    pontos_fortes = dados.get("pontos_fortes") or []
    pontos_fracos = dados.get("pontos_fracos") or []
    riscos = dados.get("riscos_tecnicos") or []
    roadmap = dados.get("roadmap") or {}
    visao_geral = dados.get("visao_geral", "")

    total_problemas = len(problemas_detectados) + len(pontos_fracos) + len(riscos)
    if modo_resposta == "leigo":
        resumo = f"Analisei seu projeto e encontrei {total_problemas} ponto(s) de atenção. A qualidade geral está {classificacao.lower()} (nota {nota}/10)."
    else:
        resumo = f"Analisei seu projeto e encontrei {total_problemas} ponto(s) de melhoria. Score: {nota}/10 — Classificação: {classificacao}."

    linhas = [
        "",
        "=" * 50,
        "  RELATÓRIO PROFISSIONAL DE ANÁLISE YUI",
        "=" * 50,
        "",
        "Score Geral: {}/10".format(nota),
        "Classificação: {}".format(classificacao),
        "",
        "Resumo rápido:",
        resumo,
        "",
        "1) VISÃO GERAL DA QUALIDADE",
        "-" * 40,
        visao_geral,
        "",
        "2) PONTOS POSITIVOS",
        "-" * 40,
    ]
    for p in pontos_fortes:
        linhas.append("  • {}".format(p))
    if not pontos_fortes:
        linhas.append("  • Estrutura do projeto identificada.")
    linhas.extend([
        "",
        "3) PROBLEMAS PRINCIPAIS",
        "-" * 40,
    ])
    for pd in problemas_detectados[:40]:
        tag = pd.get("tag", "")
        msg = pd.get("mensagem", "")
        arq = pd.get("arquivo", "")
        ln = pd.get("linha")
        linha = "  {} {}".format(tag, msg)
        if arq:
            linha += " ({})".format(arq)
        if ln:
            linha += " linha {}".format(ln)
        linhas.append(linha)
    for p in pontos_fracos:
        linhas.append("  [arquitetura] {}".format(p))
    for r in riscos:
        linhas.append("  [manutenibilidade] {}".format(r))
    if not problemas_detectados and not pontos_fracos and not riscos:
        linhas.append("  Nenhum problema crítico detectado.")
    linhas.extend([
        "",
        "4) SUGESTÕES PRÁTICAS",
        "-" * 40,
        "  Curto prazo:",
    ])
    for s in roadmap.get("curto_prazo", []):
        linhas.append("    • {}".format(s))
    linhas.extend(["  Médio prazo:"])
    for s in roadmap.get("medio_prazo", []):
        linhas.append("    • {}".format(s))
    linhas.extend(["  Longo prazo:"])
    for s in roadmap.get("longo_prazo", []):
        linhas.append("    • {}".format(s))
    linhas.extend(["", "=" * 50, ""])
    return "\n".join(linhas)
