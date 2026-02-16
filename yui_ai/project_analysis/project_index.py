"""
ProjectIndex: cache leve para análise completa de projeto.

Armazena o resultado de executar executar_analise_completa(raiz) em disco,
para evitar re-escanear o projeto a cada chamada.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from yui_ai.project_analysis.analysis_report import executar_analise_completa


_INDEX_PATH: Optional[str] = None
_TTL_HORAS = 6  # tempo de vida padrão do cache


def _get_index_path() -> str:
    global _INDEX_PATH
    if _INDEX_PATH is not None:
        return _INDEX_PATH
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    dir_path = os.path.join(base, "Yui")
    try:
        os.makedirs(dir_path, exist_ok=True)
    except OSError:
        pass
    _INDEX_PATH = os.path.join(dir_path, "project_index.json")
    return _INDEX_PATH


def _load_index() -> Dict[str, Any]:
    path = _get_index_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_index(store: Dict[str, Any]) -> None:
    path = _get_index_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _normalize_root(raiz: Optional[str]) -> str:
    return os.path.abspath(raiz or os.getcwd())


def get_cached(raiz: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Retorna (True, dados) se houver cache válido para a raiz."""
    store = _load_index()
    root = _normalize_root(raiz)
    entry = store.get(root)
    if not entry:
        return False, None
    ts = entry.get("timestamp")
    dados = entry.get("data")
    if not ts or not dados:
        return False, None
    try:
        dt = datetime.fromisoformat(ts)
    except Exception:
        return False, None
    if datetime.now() - dt > timedelta(hours=_TTL_HORAS):
        return False, None
    return True, dados


def set_cached(raiz: Optional[str], dados: Dict[str, Any]) -> None:
    store = _load_index()
    root = _normalize_root(raiz)
    store[root] = {
        "timestamp": datetime.now().isoformat(),
        "data": dados,
    }
    _save_index(store)


def get_or_compute(raiz: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Retorna (ok, dados, erro) usando cache se possível.
    Se não houver cache válido, executa a análise completa e salva no índice.
    """
    has, dados = get_cached(raiz)
    if has and dados:
        return True, dados, None

    ok, dados, err = executar_analise_completa(raiz)
    if ok and dados:
        set_cached(raiz, dados)
    return ok, dados, err

