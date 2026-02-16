"""
Capability: Web e utilidades — busca, horário, missões.
"""


def register(task_engine):
    from core.tool_runner import run_tool

    def _wrap(name):
        def _run(*args, **kwargs):
            d = kwargs if kwargs else (args[0] if args and isinstance(args[0], dict) else {})
            return run_tool(name, d)
        return _run

    for tool in ["buscar_web", "get_current_time", "create_mission", "update_mission_progress"]:
        task_engine.registrar(tool, _wrap(tool))
