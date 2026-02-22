# ==========================================================
# YUI CONTEXT BUILDER
# Analisa o projeto e monta contexto inteligente antes de enviar à IA.
# ==========================================================

import os
from typing import List

EXTENSOES_VALIDAS = (
    ".py", ".js", ".ts", ".html", ".css", ".json",
    ".md", ".yaml", ".yml", ".tsx", ".jsx",
)

IGNORAR_PASTAS = {
    "__pycache__",
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".cache",
}

MAX_ARQUIVOS = 50
MAX_CHARS = 8000


# ==========================================================
# LISTAR ARQUIVOS DO PROJETO
# ==========================================================

def listar_arquivos(raiz: str) -> List[str]:
    arquivos: List[str] = []
    raiz = os.path.abspath(raiz)
    if not os.path.isdir(raiz):
        return arquivos

    for root, dirs, files in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORAR_PASTAS]
        for f in files:
            if any(f.endswith(ext) for ext in EXTENSOES_VALIDAS):
                caminho = os.path.join(root, f)
                arquivos.append(caminho)
                if len(arquivos) >= MAX_ARQUIVOS:
                    return arquivos
    return arquivos


# ==========================================================
# LER ARQUIVO COM SEGURANÇA
# ==========================================================

def ler_arquivo(caminho: str, max_chars: int = MAX_CHARS) -> str:
    try:
        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            conteudo = f.read(max_chars)
            return conteudo
    except Exception:
        return ""


# ==========================================================
# GERAR CONTEXTO DO PROJETO
# ==========================================================

def montar_contexto_projeto(raiz: str | None = None) -> str:
    """
    Analisa a pasta do projeto, mapeia arquivos relevantes e monta
    um bloco de contexto para a IA (respeitando MAX_ARQUIVOS e MAX_CHARS).
    """
    if not raiz:
        raiz = os.getcwd()
    if not os.path.exists(raiz) or not os.path.isdir(raiz):
        return ""

    arquivos = listar_arquivos(raiz)
    if not arquivos:
        return ""

    partes: List[str] = ["### CONTEXTO DO PROJETO YUI ###\n"]

    for arq in arquivos:
        try:
            nome = os.path.relpath(arq, raiz)
        except ValueError:
            nome = arq
        codigo = ler_arquivo(arq)
        partes.append(f"\n[ARQUIVO]: {nome}\n{codigo}\n")

    return "\n".join(partes)
