"""
Scanner de projeto: lê estrutura de pastas e arquivos.
SOMENTE LEITURA. Não altera nada no projeto analisado.
"""

import os
from typing import Dict, List

IGNORAR_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "node_modules", ".mypy_cache", ".pytest_cache", "build", "dist",
}
IGNORAR_NAMES = IGNORAR_DIRS | {".DS_Store", "Thumbs.db"}


def _skip_dir(name: str) -> bool:
    return name in IGNORAR_DIRS or (name.startswith(".") and name not in (".env", ".env.example"))


def _skip_file(name: str) -> bool:
    return name in IGNORAR_NAMES or (name.startswith(".") and name not in (".env", ".env.example"))


def scan_structure(root: str) -> Dict:
    """
    Escaneia a estrutura de diretórios e arquivos do projeto.

    Args:
        root: Caminho absoluto ou relativo da raiz do projeto.

    Returns:
        Dict com: raiz, diretorios, arquivos_por_pasta, extensoes,
        total_arquivos, modulos_principais, caminhos_py.
    """
    raiz = os.path.abspath(root)
    if not os.path.isdir(raiz):
        return {
            "raiz": raiz,
            "diretorios": [],
            "arquivos_por_pasta": {},
            "extensoes": {},
            "total_arquivos": 0,
            "modulos_principais": [],
            "caminhos_py": [],
        }

    diretorios: List[str] = []
    arquivos_por_pasta: Dict[str, List[str]] = {}
    extensoes: Dict[str, int] = {}
    total = 0
    modulos_principais: List[str] = []
    caminhos_py: List[str] = []

    for _dir, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if not _skip_dir(d)]
        rel = os.path.relpath(_dir, raiz)
        pasta_nome = "[raiz]" if rel == "." else rel
        if rel == ".":
            diretorios = [d for d in dirnames if not _skip_dir(d)]

        arquivos: List[str] = []
        for f in filenames:
            if _skip_file(f):
                continue
            ext = os.path.splitext(f)[1].lower() or "(sem ext)"
            extensoes[ext] = extensoes.get(ext, 0) + 1
            arquivos.append(f)
            total += 1
            if f.endswith(".py"):
                caminhos_py.append(os.path.normpath(os.path.join(_dir, f)))

        if arquivos:
            arquivos_por_pasta[pasta_nome] = sorted(arquivos)

        if rel != "." and os.path.isfile(os.path.join(_dir, "__init__.py")):
            top = rel.split(os.sep)[0]
            if top not in modulos_principais:
                modulos_principais.append(top)

    for d in diretorios:
        if os.path.isfile(os.path.join(raiz, d, "__init__.py")) and d not in modulos_principais:
            modulos_principais.append(d)

    return {
        "raiz": raiz,
        "diretorios": sorted(diretorios),
        "arquivos_por_pasta": arquivos_por_pasta,
        "extensoes": extensoes,
        "total_arquivos": total,
        "modulos_principais": sorted(set(modulos_principais)),
        "caminhos_py": sorted(set(caminhos_py)),
    }


def list_py_files(root: str) -> List[str]:
    """Lista caminhos absolutos de todos os .py no projeto (exceto ignorados)."""
    data = scan_structure(root)
    return data.get("caminhos_py", [])
