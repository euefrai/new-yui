"""
Carregador de plugins da Yui.

Responsável por importar dinamicamente módulos em plugins/
que registram ferramentas adicionais via core.tools_registry.register_tool.
"""

import importlib
import os
import pkgutil
from typing import Optional


def load_plugins(root_path: Optional[str] = None) -> None:
    """
    Carrega todos os plugins encontrados na pasta plugins/ (se existir).

    Cada plugin deve ser um módulo Python dentro de plugins/ que, ao ser
    importado, chama register_tool(...) para registrar suas tools.
    """
    try:
        base_dir = root_path or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugins_dir = os.path.join(base_dir, "plugins")
        if not os.path.isdir(plugins_dir):
            return

        # Garante que o diretório raiz esteja no sys.path
        import sys

        if base_dir not in sys.path:
            sys.path.append(base_dir)

        import plugins  # type: ignore

        for info in pkgutil.iter_modules(plugins.__path__):
            try:
                importlib.import_module(f"plugins.{info.name}")
            except Exception:
                # Falha em um plugin não deve derrubar o servidor
                continue
    except Exception:
        return

