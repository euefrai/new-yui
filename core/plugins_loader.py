"""
Plugin Loader — Scan, register, inject into engine.

- scan: descobre plugins na pasta plugins/
- register: registra tools no tools_registry
- inject: disponibiliza ao Core Engine (action_router, agent_controller)

Plugins com --list: executados via subprocess (isolamento).
Plugins legados: carregados por import (compatibilidade).
"""

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config.settings import BASE_DIR
except Exception:
    BASE_DIR = Path(__file__).resolve().parent.parent

_PLUGIN_TOOLS: List[Dict[str, Any]] = []
_PLUGINS_LOADED = False


def scan_plugins_folder(root_path: Optional[str] = None) -> List[Path]:
    """Retorna lista de arquivos .py na pasta plugins (exceto _*.py)."""
    base = Path(root_path) if root_path else BASE_DIR
    plugins_dir = base / "plugins"
    if not plugins_dir.is_dir():
        return []
    return sorted(plugins_dir.glob("*.py"), key=lambda p: p.name)


def get_registered_plugin_tools() -> List[Dict[str, Any]]:
    """Retorna tools registradas por plugins (após load_plugins)."""
    return list(_PLUGIN_TOOLS)


def inject_into_engine() -> List[str]:
    """
    Registra plugins no engine (lazy: só carrega quando first tool é invocado).
    Retorna lista de nomes de tools padrão (plugins carregam sob demanda).
    """
    from core.tools_registry import list_tools
    tools = list_tools()
    return [t["name"] for t in tools]


def ensure_plugins_loaded() -> None:
    """Carrega plugins na primeira invocação (lazy load — evita RAM no startup)."""
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED:
        return
    _PLUGINS_LOADED = True
    load_plugins()


def load_plugins(root_path: Optional[str] = None) -> None:
    """Carrega plugins (chamado sob demanda por ensure_plugins_loaded)."""
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
                            _PLUGIN_TOOLS.append({"name": name, "plugin": str(path), "source": "subprocess"})
                    continue
        except Exception:
            pass
        # 2) Fallback: import (plugins sem --list). filesystem_plugin tem --list → subprocess.
        try:
            importlib.import_module(f"plugins.{module_name}")
            _PLUGIN_TOOLS.append({"name": module_name, "plugin": str(path), "source": "import"})
        except Exception:
            continue
