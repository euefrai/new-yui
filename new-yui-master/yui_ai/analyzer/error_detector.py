"""Detecção estática de erros e más práticas. NUNCA executa o arquivo."""
import ast
import json
import re
from typing import Any, Dict, List


def detect_issues(content: str, language: str, filename: str = "") -> List[Dict[str, Any]]:
    if language == "python":
        return _python_issues(content)
    if language == "json":
        return _json_issues(content)
    if language in ("javascript", "typescript"):
        return _js_issues(content)
    return []


def _python_issues(content: str) -> List[Dict[str, Any]]:
    issues = []
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return [{"tipo": "erro", "mensagem": f"Sintaxe: {e.msg}", "linha": e.lineno, "sugestao": "Corrija a sintaxe."}]
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append({"tipo": "má_prática", "mensagem": "except sem tipo captura tudo.", "linha": node.lineno, "sugestao": "Use except Exception: ou exceções específicas."})
        if isinstance(node, ast.ExceptHandler) and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            issues.append({"tipo": "risco", "mensagem": "Bloco except vazio pode esconder erros.", "linha": node.lineno, "sugestao": "Registre o erro (logging) ou re-raise."})
        if isinstance(node, ast.Assert):
            issues.append({"tipo": "aviso", "mensagem": "assert pode ser desativado com -O.", "linha": node.lineno, "sugestao": "Use if not cond: raise ValueError()."})
    for i, line in enumerate(content.splitlines(), 1):
        if "TODO" in line or "FIXME" in line:
            issues.append({"tipo": "aviso", "mensagem": "TODO/FIXME pendente.", "linha": i, "sugestao": "Resolva ou registre."})
        if "eval(" in line or "exec(" in line:
            issues.append({"tipo": "risco", "mensagem": "eval/exec pode ser perigoso.", "linha": i, "sugestao": "Evite com dados não confiáveis."})
        if "password" in line.lower() and "=" in line and re.search(r'["\'][^"\']+["\']', line):
            issues.append({"tipo": "risco", "mensagem": "Possível senha em texto plano.", "linha": i, "sugestao": "Use variáveis de ambiente."})
    return issues


def _json_issues(content: str) -> List[Dict[str, Any]]:
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        return [{"tipo": "erro", "mensagem": f"JSON inválido: {e.msg}", "linha": e.lineno, "sugestao": "Verifique aspas e vírgulas."}]
    return []


def _js_issues(content: str) -> List[Dict[str, Any]]:
    issues = []
    for i, line in enumerate(content.splitlines(), 1):
        if "console.log" in line:
            issues.append({"tipo": "aviso", "mensagem": "console.log em código.", "linha": i, "sugestao": "Use logger ou remova em produção."})
        if "eval(" in line:
            issues.append({"tipo": "risco", "mensagem": "eval() é inseguro.", "linha": i, "sugestao": "Evite eval; use JSON.parse."})
        if "innerHTML" in line and "=" in line:
            issues.append({"tipo": "risco", "mensagem": "innerHTML pode causar XSS.", "linha": i, "sugestao": "Prefira textContent ou sanitize."})
    return issues
