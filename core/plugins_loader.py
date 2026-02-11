"""
Carregador de plugins da Yui.

Regra: não usar import direto para execução; plugins são executados via
subprocess.run(["python", plugin_file]) para isolamento.

Plugins que suportam --list: são registrados e executados via subprocess.
Plugins legados (sem --list): ainda carregados por import (compatibilidade).
"""

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    from config.settings import BASE_DIR
except Exception:
    BASE_DIR = Path(__file__).resolve().parent.parent


def load_plugins(root_path: Optional[str] = None) -> None:
    """
    Carrega plugins da pasta plugins/.
    Preferência: executar via subprocess (--list para listar tools, invoke para rodar).
    Fallback: import dinâmico para plugins que ainda não suportam --list.
    """
    base = Path(root_path) if root_path else BASE_DIR
    plugins_dir = base / "plugins"
    if not plugins_dir.is_dir():
        return

    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    for path in sorted(plugins_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = path.stem
        # 1) Tenta subprocess: plugin com --list retorna JSON [{name, description, schema}]
        try:
            out = subprocess.run(
                [sys.executable, str(path), "--list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(base),
            )
            if out.returncode == 0 and out.stdout.strip():
                tools = json.loads(out.stdout)
                if isinstance(tools, list):
                    from core.tools_registry import register_plugin_tool
                    for t in tools:
                        name = t.get("name") or t.get("tool")
                        if name:
                            register_plugin_tool(
                                name,
                                t.get("description", ""),
                                t.get("schema"),
                                str(path),
                            )
                    continue
        except Exception:
            pass
        # 2) Fallback: import (comportamento antigo)
        try:
            importlib.import_module(f"plugins.{module_name}")
        except Exception:
            continue
