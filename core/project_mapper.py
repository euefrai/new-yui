"""
Project Mapper — gera .yui_map.json com estrutura e dependências do projeto.
Leitura sob demanda (streaming) para evitar estouro de RAM (2GB).
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

try:
    from config import settings
    SANDBOX_DIR = Path(settings.SANDBOX_DIR).resolve()
except Exception:
    SANDBOX_DIR = Path(__file__).resolve().parents[1] / "sandbox"

IGNORE_DIRS = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", ".mypy_cache", ".pytest_cache", "build", "dist"}
IGNORE_NAMES = IGNORE_DIRS | {".DS_Store", "Thumbs.db", ".yui_map.json"}
MAX_FILE_SIZE = 512 * 1024  # 512KB max por arquivo para análise de deps


def _should_skip(path: Path) -> bool:
    name = path.name
    if name in IGNORE_NAMES:
        return True
    if any(part in IGNORE_DIRS for part in path.parts):
        return True
    return False


def _iter_files_streaming(root: Path) -> Generator[Path, None, None]:
    """Itera arquivos um a um — sem carregar tudo na memória."""
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            p = Path(dirpath) / f
            if _should_skip(p):
                continue
            if p.name.startswith(".") and p.name not in (".env", ".env.example"):
                continue
            yield p


def _extract_js_imports(content: str) -> List[str]:
    """Extrai imports de JS/TS via regex (sem carregar AST completo)."""
    deps: List[str] = []
    for m in re.finditer(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", content):
        deps.append(m.group(1))
    for m in re.finditer(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
        deps.append(m.group(1))
    return deps


def _extract_py_imports(content: str) -> tuple:
    """Extrai imports Python via AST (import leve)."""
    try:
        import ast
        tree = ast.parse(content)
        std, local = [], []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    std.append(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and n.module:
                if n.level and n.level > 0:
                    local.append(n.module)
                else:
                    std.append(n.module.split(".")[0])
        return std, local
    except SyntaxError:
        return [], []


def _get_file_deps(path: Path, root: Path) -> Dict[str, Any]:
    """Analisa um arquivo e retorna dependências. Leitura sob demanda."""
    rel = path.relative_to(root)
    rel_str = str(rel).replace("\\", "/")
    ext = path.suffix.lower()
    deps: Dict[str, Any] = {"path": rel_str, "imports": []}
    try:
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            return {**deps, "imports": [], "skipped": "large_file"}
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return {**deps, "imports": [], "error": "read_failed"}
    if ext in (".py",):
        std, local = _extract_py_imports(content)
        deps["imports"] = list(set(std + local))
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        deps["imports"] = _extract_js_imports(content)
    return deps


def generate_yui_map(root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Gera um mapa do projeto com estrutura e dependências.
    Usa leitura sob demanda para cada arquivo — evita >2GB RAM.
    """
    root = root or SANDBOX_DIR
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        return {"ok": False, "error": "raiz não é diretório"}

    structure: List[str] = []
    files_deps: Dict[str, Dict] = {}
    total = 0
    for p in _iter_files_streaming(root):
        rel = str(p.relative_to(root)).replace("\\", "/")
        structure.append(rel)
        total += 1
        deps_data = _get_file_deps(p, root)
        files_deps[rel] = deps_data

    out = {
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "root": str(root),
        "structure": sorted(structure),
        "files": files_deps,
        "stats": {
            "total_files": total,
            "total_with_deps": sum(1 for f in files_deps.values() if f.get("imports")),
        },
    }

    map_path = root / ".yui_map.json"
    try:
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return {"ok": False, "error": str(e), "data": out}

    return {"ok": True, "path": str(map_path), "stats": out["stats"]}


def get_yui_map(root: Optional[Path] = None) -> Optional[Dict]:
    """Lê .yui_map.json se existir."""
    root = root or SANDBOX_DIR
    map_path = Path(root).resolve() / ".yui_map.json"
    if not map_path.is_file():
        return None
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
