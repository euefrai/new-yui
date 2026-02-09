"""
Histórico de análises da Yui.
Salva em %LOCALAPPDATA%/Yui/history.json
Cada entrada: arquivo, data, score, problemas.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

_HISTORY_PATH: Optional[str] = None


def _get_history_path() -> str:
    global _HISTORY_PATH
    if _HISTORY_PATH is not None:
        return _HISTORY_PATH
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    dir_path = os.path.join(base, "Yui")
    try:
        os.makedirs(dir_path, exist_ok=True)
    except OSError:
        pass
    _HISTORY_PATH = os.path.join(dir_path, "history.json")
    return _HISTORY_PATH


def _load_history() -> List[Dict[str, Any]]:
    path = _get_history_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(entries: List[Dict[str, Any]]) -> None:
    path = _get_history_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def salvar_historico(nome_arquivo: str, score: float, problemas: int) -> None:
    """Registra uma análise bem-sucedida no histórico."""
    entries = _load_history()
    entries.append({
        "arquivo": nome_arquivo,
        "data": datetime.now().isoformat(),
        "score": score,
        "problemas": problemas,
    })
    _save_history(entries[-100:])  # manter últimas 100


def listar_historico() -> List[Dict[str, Any]]:
    """Retorna a lista de entradas do histórico (mais recente primeiro)."""
    entries = _load_history()
    return list(reversed(entries))
