# ==========================================================
# YUI TOOL SCHEMA (registro central para o engine)
# nome, descrição, inputs, outputs, custo, nível de risco.
# ==========================================================

from typing import Any, Dict, List

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
        "description": "Gera script para compactar o projeto em ZIP.",
        "inputs": {"root_dir": "str", "zip_name": "str"},
        "outputs": ["script_path", "zip_output", "command", "ok"],
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


def get_schema(name: str) -> Dict[str, Any] | None:
    """Retorna o schema da ferramenta pelo nome."""
    for s in TOOL_SCHEMAS:
        if s.get("name") == name:
            return s
    return None


def list_for_prompt() -> str:
    """Lista ferramentas em texto para o prompt do sistema."""
    lines = []
    for t in TOOL_SCHEMAS:
        inp = ", ".join(t.get("inputs", {}).keys())
        lines.append(f"- {t['name']}({inp}): {t['description']}")
    return "\n".join(lines)
