"""
Métricas de qualidade de código (Python) para score e problemas com tags.
SOMENTE LEITURA — análise estática via AST.
"""

import ast
import os
from typing import Dict, List, Any, Tuple

IGNORAR_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", "build", "dist"}
NOMES_GENERICOS = {"job", "cb", "callback", "handler", "func", "fn", "run", "do", "main", "test", "tmp", "temp"}
MAX_LINHAS_FUNCAO = 80


def _listar_py(raiz: str) -> List[str]:
    paths = []
    for _dir, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in IGNORAR_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                paths.append(os.path.join(_dir, f))
    return paths


def _conta_linhas(source: str, node: ast.AST) -> int:
    if hasattr(node, "end_lineno") and node.end_lineno and hasattr(node, "lineno"):
        return (node.end_lineno - node.lineno) + 1
    return 0


def extrair_metricas_python(raiz: str) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    Analisa .py do projeto. Retorna (contagens_para_score, problemas_com_tags).
    contagens: empty_except, no_type_except, generic_name, long_function
    problemas: [{ "mensagem", "tag": "[arquitetura]"|"[legibilidade]"|"[manutenibilidade]", "arquivo", "linha" }]
    """
    raiz = os.path.abspath(raiz)
    paths = _listar_py(raiz)
    counts = {"empty_except": 0, "no_type_except": 0, "generic_name": 0, "long_function": 0}
    problemas: List[Dict[str, Any]] = []
    nomes_funcoes: Dict[str, List[str]] = {}  # nome -> [arquivo1, arquivo2]

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except Exception:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        rel_path = os.path.relpath(path, raiz)

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    counts["no_type_except"] += 1
                    problemas.append({
                        "mensagem": "except sem tipo (captura tudo)",
                        "tag": "[manutenibilidade]",
                        "arquivo": rel_path,
                        "linha": node.lineno,
                    })
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    counts["empty_except"] += 1
                    problemas.append({
                        "mensagem": "except vazio (pass) pode esconder erros",
                        "tag": "[manutenibilidade]",
                        "arquivo": rel_path,
                        "linha": node.lineno,
                    })
            if isinstance(node, ast.FunctionDef):
                nome = node.name
                if nome.lower() in NOMES_GENERICOS and not nome.startswith("test_"):
                    counts["generic_name"] += 1
                    problemas.append({
                        "mensagem": f"nome genérico: '{nome}'",
                        "tag": "[legibilidade]",
                        "arquivo": rel_path,
                        "linha": node.lineno,
                    })
                linhas = _conta_linhas(source, node)
                if linhas > MAX_LINHAS_FUNCAO:
                    counts["long_function"] += 1
                    problemas.append({
                        "mensagem": f"função '{nome}' muito longa ({linhas} linhas)",
                        "tag": "[manutenibilidade]",
                        "arquivo": rel_path,
                        "linha": node.lineno,
                    })
                nomes_funcoes.setdefault(nome, []).append(rel_path)

    for nome, arquivos in nomes_funcoes.items():
        if len(arquivos) > 1:
            problemas.append({
                "mensagem": f"função duplicada '{nome}' em {len(arquivos)} arquivos",
                "tag": "[arquitetura]",
                "arquivo": ", ".join(arquivos[:3]),
                "linha": None,
            })

    return counts, problemas


def calcular_score_qualidade(dados_analise: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula score a partir de 10. -1 por: except vazio, except sem tipo, nome genérico, função >80 linhas.
    Mínimo 0. Classificação: >=8 Excelente, >=6 Bom, >=4 Médio, <4 Ruim.
    """
    score = 10.0
    metricas = dados_analise.get("metricas_codigo") or {}
    if isinstance(metricas, dict):
        score -= metricas.get("empty_except", 0)
        score -= metricas.get("no_type_except", 0)
        score -= metricas.get("generic_name", 0)
        score -= metricas.get("long_function", 0)
    score = max(0, min(10, score))
    if score >= 8:
        classificacao = "Excelente"
    elif score >= 6:
        classificacao = "Bom"
    elif score >= 4:
        classificacao = "Médio"
    else:
        classificacao = "Ruim"
    return {"nota": round(score, 1), "classificacao": classificacao}
