# ==========================================================
# YUI TOOL SCHEMA (registro central para o engine)
# nome, descrição, inputs, outputs, custo, nível de risco.
# Também existe core/tool_schema.json para leitura externa.
# ==========================================================

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Schema por ferramenta: usado para escolha inteligente e prompt
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "analisar_arquivo",
        "description": "Analisa o conteúdo de um arquivo de código/texto e gera um relatório técnico.",
        "inputs": {"filename": "str", "content": "str"},
        "outputs": ["text"],
        "cost": "low",
        "risk": "low",
    },
    {
        "name": "listar_arquivos",
        "description": "Lista arquivos do projeto com filtro por pasta, padrão e limite.",
        "inputs": {"pasta": "str", "padrao": "str", "limite": "int"},
        "outputs": ["arquivos"],
        "cost": "low",
        "risk": "low",
    },
    {
        "name": "ler_arquivo_texto",
        "description": "Lê o conteúdo de um arquivo de texto (com limite de caracteres).",
        "inputs": {"caminho": "str", "max_chars": "int"},
        "outputs": ["conteudo"],
        "cost": "low",
        "risk": "low",
    },
    {
        "name": "analisar_projeto",
        "description": "Análise arquitetural completa do projeto (estrutura, riscos, roadmap).",
        "inputs": {"raiz": "str"},
        "outputs": ["texto", "resumo"],
        "cost": "high",
        "risk": "low",
    },
    {
        "name": "observar_ambiente",
        "description": "Visão rápida do projeto e sugestões de próximos passos.",
        "inputs": {"raiz": "str"},
        "outputs": ["resumo", "sugestao"],
        "cost": "medium",
        "risk": "low",
    },
    {
        "name": "criar_projeto_arquivos",
        "description": "Cria pastas e arquivos de um mini-projeto/SaaS.",
        "inputs": {"root_dir": "str", "files": "list"},
        "outputs": ["root", "files", "ok"],
        "cost": "medium",
        "risk": "medium",
    },
    {
        "name": "criar_zip_projeto",
        "description": "Gera script para compactar o projeto em ZIP. Padrão: background.",
        "inputs": {"root_dir": "str", "zip_name": "str", "background": "bool"},
        "outputs": ["script_path", "zip_output", "command", "ok", "zip_pending", "download_url"],
        "cost": "low",
        "risk": "low",
    },
    {
        "name": "consultar_indice_projeto",
        "description": "Consulta índice de análise do projeto em cache.",
        "inputs": {"raiz": "str"},
        "outputs": ["texto", "resumo"],
        "cost": "low",
        "risk": "low",
    },
]


def get_schema(name: str) -> Optional[Dict[str, Any]]:
    """Retorna o schema da ferramenta pelo nome."""
    for s in TOOL_SCHEMAS:
        if s.get("name") == name:
            return s
    return None


def load_from_json(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Carrega schemas do JSON (fallback se core/tool_schema.json existir)."""
    p = Path(path or __file__).parent / "tool_schema.json"
    if not p.exists():
        return TOOL_SCHEMAS
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return TOOL_SCHEMAS


def list_for_prompt(schemas: Optional[List[Dict[str, Any]]] = None) -> str:
    """Lista ferramentas em texto para o prompt do sistema."""
    tools = schemas or TOOL_SCHEMAS
    lines = []
    for t in tools:
        inp = t.get("inputs")
        inp_str = ", ".join(inp.keys()) if isinstance(inp, dict) else ", ".join(inp or [])
        lines.append(f"- {t['name']}({inp_str}): {t['description']}")
    return "\n".join(lines)


def get_by_risk(risk: str) -> list:
    """Retorna ferramentas com o nível de risco indicado (low, medium, high)."""
    return [t for t in TOOL_SCHEMAS if t.get("risk") == risk]


def get_by_cost(cost: str) -> list:
    """Retorna ferramentas com o custo indicado (low, medium, high)."""
    return [t for t in TOOL_SCHEMAS if t.get("cost") == cost]
