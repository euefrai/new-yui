"""
Capability: Editor de código — criar/editar/deletar arquivos no sandbox.
"""


def register(task_engine):
    from core.tool_runner import run_tool

    def _wrap(name):
        def _run(*args, **kwargs):
            d = kwargs if kwargs else (args[0] if args and isinstance(args[0], dict) else {})
            return run_tool(name, d)
        return _run

    for tool in ["fs_create_file", "fs_create_folder", "fs_delete_file"]:
        task_engine.registrar(tool, _wrap(tool))
