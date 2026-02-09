"""Scanner de projeto: lê estrutura de pastas e arquivos. SOMENTE LEITURA."""
import os
from typing import Dict, Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_DIR = os.path.dirname(_THIS_DIR)
DEFAULT_PROJECT_ROOT = os.path.dirname(_PACKAGE_DIR)

IGNORAR = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache"}


def _skip(nome: str) -> bool:
    return nome in IGNORAR or (nome.startswith(".") and nome not in (".env", ".env.example"))


def escanear_estrutura(raiz: Optional[str] = None) -> Dict:
    """Lê estrutura de diretórios e arquivos. Retorna raiz, diretorios, arquivos_por_pasta, extensoes, total_arquivos, modulos_principais."""
    raiz = os.path.abspath(raiz or DEFAULT_PROJECT_ROOT)
    if not os.path.isdir(raiz):
        return {"raiz": raiz, "diretorios": [], "arquivos_por_pasta": {}, "extensoes": {}, "total_arquivos": 0, "modulos_principais": []}
    diretorios = []
    arquivos_por_pasta = {}
    extensoes = {}
    total = 0
    modulos_principais = []
    for _dir, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if not _skip(d)]
        rel = os.path.relpath(_dir, raiz)
        pasta_nome = "[raiz]" if rel == "." else rel
        if rel == ".":
            diretorios = [d for d in dirnames if not _skip(d)]
        arquivos = []
        for f in filenames:
            if _skip(f):
                continue
            ext = os.path.splitext(f)[1].lower() or "(sem ext)"
            extensoes[ext] = extensoes.get(ext, 0) + 1
            arquivos.append(f)
            total += 1
        if arquivos:
            arquivos_por_pasta[pasta_nome] = sorted(arquivos)
        if rel != "." and os.path.isfile(os.path.join(_dir, "__init__.py")):
            top = rel.split(os.sep)[0]
            if top not in modulos_principais:
                modulos_principais.append(top)
    for d in diretorios:
        if os.path.isfile(os.path.join(raiz, d, "__init__.py")) and d not in modulos_principais:
            modulos_principais.append(d)
    return {"raiz": raiz, "diretorios": sorted(diretorios), "arquivos_por_pasta": arquivos_por_pasta, "extensoes": extensoes, "total_arquivos": total, "modulos_principais": sorted(set(modulos_principais))}
