# ==========================================================
# YUI WORKSPACE INDEXER — Mapa Mental do Projeto
#
# NÃO é RAG. NÃO é memória longa.
# É um snapshot leve do projeto atual.
#
# Sem index: IA lê arquivos toda hora.
# Com index: IA já sabe onde está tudo.
# ==========================================================

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config import settings
    SANDBOX_DIR = Path(settings.SANDBOX_DIR).resolve()
    BASE_DIR = Path(settings.BASE_DIR).resolve()
except Exception:
    BASE_DIR = Path(__file__).resolve().parents[1]
    SANDBOX_DIR = BASE_DIR / "sandbox"

IGNORE_DIRS = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", ".mypy_cache", ".pytest_cache", "build", "dist"}
IGNORE_NAMES = IGNORE_DIRS | {".DS_Store", "Thumbs.db"}

# Extensões → chave no mapa
EXT_MAP = {
    ".py": "python",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".js": "js",
    ".mjs": "js",
    ".ts": "ts",
    ".tsx": "ts",
    ".jsx": "js",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _should_skip(path: Path, root: Path) -> bool:
    """Ignora pastas e arquivos desnecessários."""
    rel = path.relative_to(root)
    for part in rel.parts:
        if part in IGNORE_DIRS or part.startswith(".") and part not in (".env", ".env.example"):
            return True
    if path.name in IGNORE_NAMES:
        return True
    return False


def scan(base_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Escaneia o workspace e retorna mapa leve.
    Retorno: { python: [...], html: [...], css: [...], js: [...], total, extensoes }
    Caminhos relativos ao base_path.
    """
    root = Path(base_path or SANDBOX_DIR).resolve()
    if not root.is_dir():
        return _empty_map(str(root))

    mapa: Dict[str, List[str]] = {
        "python": [],
        "html": [],
        "css": [],
        "js": [],
        "ts": [],
        "json": [],
        "markdown": [],
        "text": [],
        "yaml": [],
    }
    extensoes: Dict[str, int] = {}
    total = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f in IGNORE_NAMES:
                continue
            full = Path(dirpath) / f
            try:
                rel = full.relative_to(root)
            except ValueError:
                continue
            if _should_skip(full, root):
                continue
            ext = full.suffix.lower()
            key = EXT_MAP.get(ext)
            if key and key in mapa:
                rel_str = str(rel).replace("\\", "/")
                mapa[key].append(rel_str)
            extensoes[ext or "(sem ext)"] = extensoes.get(ext or "(sem ext)", 0) + 1
            total += 1

    return {
        "python": mapa["python"],
        "html": mapa["html"],
        "css": mapa["css"],
        "js": mapa["js"],
        "ts": mapa["ts"],
        "json": mapa["json"],
        "markdown": mapa["markdown"],
        "text": mapa["text"],
        "yaml": mapa["yaml"],
        "total": total,
        "extensoes": extensoes,
        "raiz": str(root),
    }


def _empty_map(raiz: str) -> Dict[str, Any]:
    return {
        "python": [], "html": [], "css": [], "js": [], "ts": [], "json": [],
        "markdown": [], "text": [], "yaml": [],
        "total": 0, "extensoes": {}, "raiz": raiz,
    }


def to_prompt_snippet(mapa: Dict[str, Any], ultimo_editado: Optional[str] = None) -> str:
    """
    Gera snippet para injetar no prompt.
    Ex: "Projeto: 12 arquivos Python, 3 HTML, 2 CSS. Último editado: app.py."
    """
    if not mapa or mapa.get("total", 0) == 0:
        return ""
    parts = []
    for key in ("python", "html", "css", "js", "ts"):
        lst = mapa.get(key) or []
        if lst:
            parts.append(f"{len(lst)} {key}")
    if not parts:
        return ""
    txt = f"Projeto: {', '.join(parts)}. Total: {mapa.get('total', 0)} arquivos."
    if ultimo_editado:
        txt += f" Último editado: {ultimo_editado}."
    return f"[Workspace Index] {txt}\n\n"


def should_split_task(mapa: Dict[str, Any], threshold: int = 10) -> bool:
    """
    Sugere dividir tarefa quando muitas arquivos (evita pico CPU).
    Ex: len(python) > 10 → planner pode quebrar em partes.
    """
    py_count = len(mapa.get("python") or [])
    total = mapa.get("total") or 0
    return py_count > threshold or total > threshold * 2
