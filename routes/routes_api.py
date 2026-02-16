"""Compat layer: preserva imports legados de `routes.routes_api`.

Este módulo reexporta todos os símbolos públicos de `web.routes.routes_api`
para manter retrocompatibilidade de código que ainda importa funções/blueprints
por este caminho legado.
"""

from web.routes.routes_api import *  # noqa: F401,F403
