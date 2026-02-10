"""
Plugin de sistema de arquivos (modo seguro, somente leitura por padrão).

Ferramentas expostas:
- listar_arquivos: lista arquivos em uma pasta (com limite e filtro simples).
- ler_arquivo_texto: lê conteúdo de um arquivo de texto (até max_chars).
"""

import fnmatch
import os
from typing import Dict, List

from core.tools_registry import register_tool


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def _resolver_caminho(rel_path: str) -> str:
    """Resolve caminho relativo dentro do projeto, evitando sair da raiz."""
    rel_path = rel_path or "."
    base = PROJECT_ROOT
    full = os.path.abspath(os.path.join(base, rel_path))
    # Proteção simples: impede escapar para fora do root do projeto
    if not full.startswith(os.path.dirname(base)):
        return base
    return full


def tool_listar_arquivos(pasta: str = ".", padrao: str = "*", limite: int = 100) -> Dict:
    pasta_abs = _resolver_caminho(pasta)
    if not os.path.isdir(pasta_abs):
        return {"ok": False, "arquivos": [], "error": f"Pasta não encontrada: {pasta}"}
    arquivos: List[str] = []
    try:
        for root, _, files in os.walk(pasta_abs):
            rel_root = os.path.relpath(root, pasta_abs)
            for f in files:
                if fnmatch.fnmatch(f, padrao):
                    caminho_rel = os.path.join(rel_root, f) if rel_root != "." else f
                    arquivos.append(caminho_rel)
                    if len(arquivos) >= max(1, min(limite, 500)):
                        break
            if len(arquivos) >= max(1, min(limite, 500)):
                break
        return {"ok": True, "arquivos": arquivos, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "arquivos": [], "error": str(e)}


def tool_ler_arquivo_texto(caminho: str, max_chars: int = 4000) -> Dict:
    if not caminho:
        return {"ok": False, "conteudo": "", "error": "caminho obrigatório"}
    pasta_base = PROJECT_ROOT
    full = _resolver_caminho(caminho)
    if not os.path.isfile(full):
        return {"ok": False, "conteudo": "", "error": f"Arquivo não encontrado: {caminho}"}
    try:
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            conteudo = f.read(max_chars)
        return {"ok": True, "conteudo": conteudo, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "conteudo": "", "error": str(e)}


# Registro das ferramentas deste plugin
register_tool(
    name="listar_arquivos",
    fn=tool_listar_arquivos,
    description="Lista arquivos em uma pasta do projeto (somente leitura).",
    schema={
        "pasta": "Caminho relativo à raiz dos plugins (padrão: .).",
        "padrao": "Padrão glob simples (ex: *.py).",
        "limite": "Número máximo de arquivos retornados (padrão: 100).",
    },
)

register_tool(
    name="ler_arquivo_texto",
    fn=tool_ler_arquivo_texto,
    description="Lê conteúdo de um arquivo de texto no projeto (somente leitura, limitado por max_chars).",
    schema={
        "caminho": "Caminho relativo ao projeto (ex: yui_ai/main.py).",
        "max_chars": "Número máximo de caracteres a retornar (padrão: 4000).",
    },
)

