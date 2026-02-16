"""
Capability: Análise de código e projeto.
"""


def register(task_engine):
    from core.tool_runner import run_tool

    def _wrap(name):
        def _run(*args, **kwargs):
            d = kwargs if kwargs else (args[0] if args and isinstance(args[0], dict) else {})
            return run_tool(name, d)
        return _run

    for tool in ["analisar_projeto", "analisar_arquivo", "observar_ambiente", "consultar_indice_projeto", "generate_project_map"]:
        task_engine.registrar(tool, _wrap(tool))
