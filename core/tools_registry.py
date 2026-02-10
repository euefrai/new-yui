"""
Registro central de ferramentas (tools) que a Yui pode chamar.

Cada ferramenta tem:
- name: identificador único (string)
- description: descrição curta
- fn: função Python que implementa a ferramenta
- schema: descrição simples dos parâmetros esperados (opcional)
"""

from typing import Any, Callable, Dict, List, Optional


ToolFn = Callable[..., Any]


_TOOLS: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    fn: ToolFn,
    description: str,
    schema: Optional[Dict[str, Any]] = None,
) -> None:
    """Registra uma ferramenta no registry global."""
    _TOOLS[name] = {
        "name": name,
        "fn": fn,
        "description": description,
        "schema": schema or {},
    }


def list_tools() -> List[Dict[str, Any]]:
    """Retorna metadados de todas as ferramentas registradas (sem a função)."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "schema": t.get("schema", {}),
        }
        for t in _TOOLS.values()
    ]


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """Obtém a ferramenta completa (incluindo fn) pelo nome."""
    return _TOOLS.get(name)


def _init_default_tools() -> None:
    """Ponto central para registrar ferramentas padrão."""
    from core.tools_runtime import (
        tool_analisar_arquivo,
        tool_analisar_projeto,
        tool_observar_ambiente,
        tool_criar_projeto_arquivos,
        tool_criar_zip_projeto,
        tool_consultar_indice_projeto,
    )
    from core.plugins_loader import load_plugins

    register_tool(
        name="analisar_arquivo",
        fn=tool_analisar_arquivo,
        description="Analisa o conteúdo de um arquivo de código/texto e gera um relatório técnico.",
        schema={
            "filename": "Nome do arquivo (ex: main.py)",
            "content": "Conteúdo completo do arquivo em texto.",
        },
    )

    register_tool(
        name="analisar_projeto",
        fn=tool_analisar_projeto,
        description="Executa uma análise arquitetural completa do projeto atual (estrutura, riscos, roadmap).",
        schema={
            "raiz": "Caminho raiz do projeto (opcional). Se omitido, usa o diretório padrão do analisador.",
        },
    )

    register_tool(
        name="observar_ambiente",
        fn=tool_observar_ambiente,
        description="Observa rapidamente a estrutura do projeto e sugere próximos passos (ex.: analisar arquitetura).",
        schema={
            "raiz": "Caminho raiz do projeto (opcional). Se omitido, usa o diretório padrão.",
        },
    )

    register_tool(
        name="criar_projeto_arquivos",
        fn=tool_criar_projeto_arquivos,
        description="Cria fisicamente um mini-projeto (pastas e arquivos) a partir de uma lista de arquivos.",
        schema={
            "root_dir": "Nome/base da pasta do projeto (relativa a generated_projects).",
            "files": "Lista de arquivos { path, content } a serem criados.",
        },
    )

    register_tool(
        name="criar_zip_projeto",
        fn=tool_criar_zip_projeto,
        description="Gera um script Python para compactar uma pasta de projeto em ZIP, ignorando arquivos sensíveis.",
        schema={
            "root_dir": "Pasta do projeto (ex: generated_projects/meu_saas).",
            "zip_name": "Nome opcional do zip (sem extensão).",
        },
    )

    register_tool(
        name="consultar_indice_projeto",
        fn=tool_consultar_indice_projeto,
        description="Consulta o índice de análise de projeto em cache (visão geral, pontos fortes/fracos, riscos, roadmap).",
        schema={
            "raiz": "Caminho raiz do projeto (opcional). Se omitido, usa o diretório padrão.",
        },
    )

    # Carrega plugins externos (se houver)
    load_plugins()


# Inicializa tools padrão no import
_init_default_tools()

