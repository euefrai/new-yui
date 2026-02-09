"""
Mapeador de dependências: extrai imports de arquivos .py via AST.
SOMENTE LEITURA. Construção de grafo de módulos para análise.
"""

import ast
import os
from typing import Dict, List, Optional, Set, Tuple

from yui_ai.analyzer.project_scanner import list_py_files, scan_structure


def _path_to_module(root: str, path: str) -> str:
    """Converte caminho absoluto para nome de módulo (estilo Python)."""
    rel = os.path.relpath(path, root)
    rel = rel.replace("\\", "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith("/__init__"):
        rel = rel[:-9]
    return rel.replace("/", ".").replace(".__init__", "")


def _extract_imports_from_code(code: str, path: str) -> Tuple[List[str], List[str]]:
    """
    Extrai módulos importados de um código Python via AST.
    Retorna (imports_absolutos, imports_relativos_ou_locais).
    """
    std_imports: List[str] = []
    local_imports: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return std_imports, local_imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("."):
                    local_imports.append(name)
                else:
                    std_imports.append(name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if node.level and node.level > 0:
                    local_imports.append(node.module)
                else:
                    std_imports.append(node.module.split(".")[0])
            else:
                local_imports.append(".")

    return std_imports, local_imports


def _resolve_local_module(root: str, file_path: str, import_module: str, level: int) -> Optional[str]:
    """
    Resolve import relativo (from .x import) para nome de módulo no projeto.
    Simplificado: só considera primeiro nível do projeto (pastas na raiz).
    """
    dir_file = os.path.dirname(file_path)
    if level == 0:
        return import_module.split(".")[0] if import_module else None
    parts = import_module.split(".") if import_module else []
    for _ in range(level - 1):
        dir_file = os.path.dirname(dir_file)
    if not parts:
        # from . import x → pasta atual
        rel = os.path.relpath(dir_file, root)
        return rel.replace("\\", "/").split("/")[0] if rel != "." else None
    # from .sub import x → sub
    return parts[0] if parts else None


def build_dependency_graph(root: str) -> Dict:
    """
    Constrói grafo de dependências a partir dos arquivos .py do projeto.

    Returns:
        Dict com:
        - nodes: { modulo: { "path", "imports_std", "imports_local", "funcoes", "classes" } }
        - edges: [ (from_module, to_module), ... ]
        - circular: [ [mod1, mod2, ...], ... ] ciclos detectados
        - stats: { total_arquivos, total_imports_internos, etc }
    """
    root = os.path.abspath(root)
    paths = list_py_files(root)
    scan_data = scan_structure(root)
    modulos_projeto = set(scan_data.get("modulos_principais", []))
    nodes: Dict[str, Dict] = {}
    edges: List[Tuple[str, str]] = []
    encoding = "utf-8"

    for path in paths:
        try:
            with open(path, "r", encoding=encoding) as f:
                code = f.read()
        except Exception:
            continue

        mod = _path_to_module(root, path)
        std_imp, local_imp = _extract_imports_from_code(code, path)

        funcoes: List[str] = []
        classes: List[str] = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    funcoes.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
        except SyntaxError:
            pass

        nodes[mod] = {
            "path": path,
            "imports_std": std_imp,
            "imports_local": local_imp,
            "funcoes": funcoes,
            "classes": classes,
        }

        for imp in std_imp:
            top = imp.split(".")[0]
            if top in modulos_projeto and top != mod.split(".")[0]:
                edges.append((mod, top))
        for loc in local_imp:
            if loc.startswith("."):
                level = len(loc) - len(loc.lstrip("."))
                resolved = _resolve_local_module(root, path, loc.lstrip("."), level)
                if resolved and resolved in modulos_projeto:
                    edges.append((mod, resolved))

    circular = _find_circular_deps(edges)
    total_internal = sum(1 for a, b in edges if a and b)

    return {
        "nodes": nodes,
        "edges": edges,
        "circular": circular,
        "stats": {
            "total_arquivos_py": len(nodes),
            "total_arestas": len(edges),
            "total_imports_internos": total_internal,
            "ciclos": len(circular),
        },
    }


def _find_circular_deps(edges: List[Tuple[str, str]]) -> List[List[str]]:
    """Detecta ciclos no grafo de dependências (por módulo top-level)."""
    from collections import defaultdict

    # Simplificar: agrupar por primeiro segmento do módulo (pasta)
    def top(m: str) -> str:
        return m.split(".")[0] if m else ""

    adj: Dict[str, Set[str]] = defaultdict(set)
    for a, b in edges:
        ta, tb = top(a), top(b)
        if ta and tb and ta != tb:
            adj[ta].add(tb)

    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []
    path_set: Set[str] = set()
    cycle_nodes: Set[str] = set()

    def dfs(v: str) -> bool:
        visited.add(v)
        rec_stack.add(v)
        path.append(v)
        path_set.add(v)
        for w in adj.get(v, []):
            if w not in visited:
                if dfs(w):
                    return True
            elif w in rec_stack:
                idx = path.index(w)
                cycle = path[idx:] + [w]
                cycle_nodes.update(cycle)
                cycles.append(cycle)
                return True
        rec_stack.discard(v)
        path.pop()
        path_set.discard(v)
        return False

    for node in adj:
        if node not in visited:
            dfs(node)

    return cycles
