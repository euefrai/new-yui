"""Análise estática do propósito e estrutura do arquivo. NUNCA executa."""
import ast
import json
import re
from typing import Any, Dict, List

EXTENSION_LANGUAGE = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".mjs": "javascript", ".cjs": "javascript", ".json": "json",
    ".txt": "text", ".md": "markdown", ".html": "html", ".css": "css",
    ".yml": "yaml", ".yaml": "yaml", ".java": "java",
}


def get_language(filename: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return EXTENSION_LANGUAGE.get(ext, "text")


def analyze_file(content: str, language: str, filename: str = "") -> Dict[str, Any]:
    funcao = _infer_purpose(content, language, filename)
    estrutura = _extract_structure(content, language)
    return {"funcao": funcao, "estrutura": estrutura, "linguagem": language}


def _infer_purpose(content: str, language: str, filename: str) -> str:
    if language == "python":
        return _python_purpose(content, filename)
    if language == "json":
        try:
            d = json.loads(content)
            if isinstance(d, dict) and ("dependencies" in d or "scripts" in d):
                return "Manifest de dependências ou configuração (ex.: package.json)."
            return "Dados em JSON."
        except json.JSONDecodeError:
            pass
    if language in ("javascript", "typescript"):
        if "export " in content or "module.exports" in content:
            return "Módulo JS/TS (exporta funções ou componentes)."
        return "Script ou módulo JavaScript/TypeScript."
    if language == "text":
        return "Arquivo de texto."
    if language == "markdown":
        return "Documentação em Markdown."
    return "Arquivo de código ou texto."


def _python_purpose(content: str, filename: str) -> str:
    if "def test_" in content or "unittest" in content or "pytest" in content:
        return "Arquivo de testes."
    if "__name__" in content and "__main__" in content:
        return "Script executável."
    if "flask" in content.lower() or "fastapi" in content.lower():
        return "Aplicação ou rotas web (backend)."
    return "Módulo Python (lógica ou utilitários)."


def _extract_structure(content: str, language: str) -> List[Dict[str, Any]]:
    if language == "python":
        return _python_structure(content)
    if language == "json":
        return _json_structure(content)
    if language in ("javascript", "typescript"):
        return _js_structure(content)
    return [{"tipo": "arquivo", "linhas": len(content.splitlines())}]


def _python_structure(content: str) -> List[Dict[str, Any]]:
    items = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                items.append({"tipo": "função", "nome": node.name, "linha": node.lineno})
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                items.append({"tipo": "classe", "nome": node.name, "linha": node.lineno, "metodos": methods})
    except SyntaxError:
        items.append({"tipo": "erro_sintaxe", "mensagem": "Não foi possível parsear."})
    return items or [{"tipo": "script", "linhas": len(content.splitlines())}]


def _json_structure(content: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return [{"tipo": "chave", "nome": k} for k in list(data.keys())[:30]]
        if isinstance(data, list):
            return [{"tipo": "array", "tamanho": len(data)}]
    except json.JSONDecodeError:
        return [{"tipo": "erro", "mensagem": "JSON inválido."}]
    return []


def _js_structure(content: str) -> List[Dict[str, Any]]:
    items = []
    for m in re.finditer(r"function\s+(\w+)\s*\(", content):
        items.append({"tipo": "função", "nome": m.group(1)})
    for m in re.finditer(r"class\s+(\w+)", content):
        items.append({"tipo": "classe", "nome": m.group(1)})
    return items or [{"tipo": "script", "linhas": len(content.splitlines())}]
