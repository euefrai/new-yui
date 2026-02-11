"""
Linter de sintaxe: valida Python e JS/TS antes de exibir no Workspace.
Retorna erros para correção automática pela IA.
"""

import ast
import re
from typing import Dict, List, Optional, Tuple


def _lint_python(code: str, path: str = "") -> List[Dict[str, str]]:
    """Valida sintaxe Python via AST."""
    errors: List[Dict[str, str]] = []
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append({
            "path": path,
            "lang": "python",
            "line": e.lineno or 0,
            "message": str(e.msg) if e.msg else str(e),
            "text": (e.text or "").strip(),
        })
    return errors


def _lint_javascript(code: str, path: str = "") -> List[Dict[str, str]]:
    """
    Validação básica de JS/TS (regex para erros comuns).
    Não substitui um parser completo, mas detecta estruturas quebradas.
    """
    errors: List[Dict[str, str]] = []
    lines = code.split("\n")
    parens, brackets, braces = 0, 0, 0
    in_string = None
    escape = False
    for i, line in enumerate(lines, 1):
        j = 0
        while j < len(line):
            c = line[j]
            if escape:
                escape = False
                j += 1
                continue
            if c == "\\" and in_string:
                escape = True
                j += 1
                continue
            if in_string:
                if c == in_string:
                    in_string = None
                j += 1
                continue
            if c in ("'", '"', "`"):
                in_string = c
                j += 1
                continue
            if c == "(":
                parens += 1
            elif c == ")":
                parens -= 1
            elif c == "[":
                brackets += 1
            elif c == "]":
                brackets -= 1
            elif c == "{":
                braces += 1
            elif c == "}":
                braces -= 1
            j += 1
        if parens < 0 or brackets < 0 or braces < 0:
            break
    if parens != 0 or brackets != 0 or braces != 0:
        errors.append({
            "path": path,
            "lang": "javascript",
            "line": 0,
            "message": "Parênteses, colchetes ou chaves desbalanceados",
            "text": "",
        })
    return errors


def lint_code(content: str, path: str = "", lang: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Valida sintaxe do código. Retorna lista de erros.
    path: usado para identificar o arquivo nas mensagens.
    lang: "python", "javascript", "typescript" ou inferido por extensão.
    """
    if not content or not content.strip():
        return []
    lang = (lang or "").lower()
    if not lang and path:
        ext = path.split(".")[-1].lower()
        ext_map = {"py": "python", "js": "javascript", "jsx": "javascript", "ts": "javascript", "tsx": "javascript"}
        lang = ext_map.get(ext, "")
    if lang in ("python", "py"):
        return _lint_python(content, path)
    if lang in ("javascript", "js", "typescript", "ts", "jsx", "tsx"):
        return _lint_javascript(content, path)
    return []


def lint_multi_write_actions(actions: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """
    Aplica lint em cada ação create/update que tem content.
    Retorna (actions_corrigidas, erros_formatados).
    """
    all_errors: List[str] = []
    fixed_actions: List[Dict] = []
    for a in actions:
        action = a.get("action", "")
        path = a.get("path", "")
        content = a.get("content", "")
        if action in ("create", "update") and content:
            ext = path.split(".")[-1].lower()
            lang = "python" if ext == "py" else "javascript"
            errs = lint_code(content, path, lang)
            if errs:
                for e in errs:
                    all_errors.append(f"{path}:{e.get('line', 0)} - {e.get('message', '')}")
        fixed_actions.append(a)
    return fixed_actions, all_errors
