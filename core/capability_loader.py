# ==========================================================
# YUI CAPABILITY LOADER — Sistema de Plugins Dinâmicos
#
# Qualquer arquivo cap_*.py dentro core/capability_plugins/ vira uma skill automaticamente.
# Sem hardcode. Core = estável. Capabilities = experimentais.
#
# Inicialização: carregar_capabilities(task_engine)
# ==========================================================

import importlib
from pathlib import Path
from typing import Any, List, Optional

try:
    from config.settings import BASE_DIR
except Exception:
    BASE_DIR = Path(__file__).resolve().parent.parent

_CAPABILITIES_DIR = Path(__file__).resolve().parent / "capability_plugins"
_LOADED: List[str] = []


def get_capabilities_dir() -> Path:
    """Retorna o diretório de capabilities."""
    return _CAPABILITIES_DIR


def carregar_capabilities(task_engine: Any) -> List[str]:
    """
    Escaneia core/capability_plugins/ e chama register(task_engine) em cada módulo.
    Retorna lista de capabilities carregadas.
    """
    global _LOADED
    if _LOADED:
        return _LOADED

    loaded: List[str] = []
    cap_dir = get_capabilities_dir()
    if not cap_dir.is_dir():
        return loaded

    for path in sorted(cap_dir.glob("cap_*.py")):
        if path.name.startswith("_"):
            continue
        module_name = path.stem
        try:
            mod = importlib.import_module(f"core.capability_plugins.{module_name}")
            if hasattr(mod, "register"):
                mod.register(task_engine)
                loaded.append(module_name)
        except Exception as e:
            try:
                from core.observability import record_activity
                record_activity("capability_loader", f"Falha ao carregar {module_name}", str(e))
            except Exception:
                pass
            continue

    _LOADED = loaded
    return loaded


def list_loaded() -> List[str]:
    """Retorna capabilities já carregadas."""
    return list(_LOADED)


def reset() -> None:
    """Limpa cache (útil para testes)."""
    global _LOADED
    _LOADED = []
