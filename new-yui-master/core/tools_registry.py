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


def _plugin_runner(plugin_path: str, tool_name: str):
    """Retorna uma função que executa o plugin via subprocess (isolamento)."""
    import json
    import subprocess
    import sys

    def run(**kwargs):
        try:
            out = subprocess.run(
                [sys.executable, plugin_path, "invoke", tool_name, json.dumps(kwargs)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(plugin_path.parent) if hasattr(plugin_path, "parent") else None,
            )
            if out.returncode != 0:
                return {"ok": False, "error": out.stderr or "Plugin failed"}
            if not out.stdout.strip():
                return {"ok": True, "result": None}
            return json.loads(out.stdout)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return run


def register_plugin_tool(
    name: str,
    description: str,
    schema: Optional[Dict[str, Any]],
    plugin_path: str,
) -> None:
    """Registra uma ferramenta que será executada via subprocess (plugin isolado)."""
    from pathlib import Path
    path = Path(plugin_path).resolve()
    _TOOLS[name] = {
        "name": name,
        "fn": _plugin_runner(path, name),
        "description": description,
        "schema": schema or {},
        "plugin_path": str(path),
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
        tool_get_current_time,
        tool_buscar_web,
        tool_fs_create_file,
        tool_fs_create_folder,
        tool_fs_delete_file,
        tool_generate_project_map,
    )

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

    register_tool(
        name="get_current_time",
        fn=tool_get_current_time,
        description="Retorna o horário e data atuais em Brasília/São Paulo. Use quando o usuário perguntar as horas, data ou saudação (Bom dia/Boa tarde).",
        schema={},
    )

    register_tool(
        name="buscar_web",
        fn=tool_buscar_web,
        description="Busca informações na web (DuckDuckGo). Use para verificar dados externos, notícias ou informações que você não tem certeza.",
        schema={
            "query": "Termo de busca (ex: clima São Paulo hoje).",
            "limite": "Máximo de resultados (opcional, padrão 5).",
        },
    )

    register_tool(
        name="fs_create_file",
        fn=tool_fs_create_file,
        description="File System Bridge: cria ou sobrescreve arquivo no sandbox do projeto (workspace).",
        schema={
            "path": "Caminho relativo do arquivo (ex: src/main.py, index.html).",
            "content": "Conteúdo do arquivo em texto.",
        },
    )

    register_tool(
        name="fs_create_folder",
        fn=tool_fs_create_folder,
        description="File System Bridge: cria pasta no sandbox do projeto.",
        schema={
            "path": "Caminho relativo da pasta (ex: src/components).",
        },
    )

    register_tool(
        name="fs_delete_file",
        fn=tool_fs_delete_file,
        description="File System Bridge: deleta arquivo ou pasta no sandbox do projeto.",
        schema={
            "path": "Caminho relativo do arquivo ou pasta a deletar.",
        },
    )

    register_tool(
        name="generate_project_map",
        fn=tool_generate_project_map,
        description="Project Mapper: gera .yui_map.json com estrutura e dependências do projeto (leitura sob demanda).",
        schema={
            "root": "Caminho raiz (opcional). Se omitido, usa sandbox.",
        },
    )

    from core.project_manager import create_mission as pm_create_mission, update_mission_progress

    def _tool_create_mission(project: str, goal: str, tasks: Optional[List[str]] = None):
        """Cria missão persistente (Project Brain). user_id/chat_id vêm do contexto do agente."""
        tasks = tasks or []
        if isinstance(tasks, str):
            tasks = [t.strip() for t in tasks.split(",") if t.strip()]
        user_id, chat_id = ("", "")
        try:
            from core.agent_context import get_agent_context
            user_id, chat_id = get_agent_context()
        except Exception:
            pass
        mission = pm_create_mission(
            project=project.strip(),
            goal=goal.strip(),
            tasks=tasks,
            user_id=user_id or "",
            chat_id=chat_id or "",
        )
        return {"ok": True, "mission": mission.to_dict()}

    register_tool(
        name="create_mission",
        fn=_tool_create_mission,
        description="Project Brain: cria uma missão persistente com objetivo e tarefas. Use quando o usuário definir um objetivo de longo prazo.",
        schema={
            "project": "Nome do projeto/missão (ex: Autono+ SaaS).",
            "goal": "Objetivo principal da missão.",
            "tasks": "Lista opcional de tarefas ou string separada por vírgulas.",
        },
    )

    def _tool_update_mission_progress(project: str, task_completed: str = "", progress_delta: float = 0.0, current_task: str = ""):
        """Atualiza progresso da missão ativa (Project Brain)."""
        ok = update_mission_progress(
            project=project,
            task_completed=task_completed if task_completed else None,
            progress_delta=progress_delta,
            current_task=current_task if current_task else None,
        )
        return {"ok": ok, "message": "Progresso atualizado" if ok else "Missão não encontrada"}

    register_tool(
        name="update_mission_progress",
        fn=_tool_update_mission_progress,
        description="Project Brain: atualiza o progresso da missão ativa após concluir uma tarefa. Use quando terminar uma etapa da missão.",
        schema={
            "project": "Nome do projeto da missão (ex: Autono+ SaaS).",
            "task_completed": "Tarefa que acabou de concluir (remover da lista).",
            "progress_delta": "Incremento de progresso (0.0 a 1.0, ex: 0.2 = +20%).",
            "current_task": "Próxima tarefa em foco.",
        },
    )

    # Plugins: lazy load (ensure_plugins_loaded no tool_runner)


# Inicializa tools padrão no import
_init_default_tools()

