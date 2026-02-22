"""Compat layer: preserva imports legados de `routes.routes_api`.

Este módulo reexporta todos os símbolos públicos de `web.routes.routes_api`
para manter retrocompatibilidade de código que ainda importa funções/blueprints
por este caminho legado.
"""

from web.routes.routes_api import (
    main_bp,
    file_bp,
    tool_bp,
    system_bp,
    sandbox_bp,
    goals_bp,
    missions_bp,
    clear_chat,
    index,
    api_upload,
    api_analyze_file,
    api_list_tools,
    api_run_tool,
)
