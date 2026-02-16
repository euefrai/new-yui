"""
Configuração central de logging para a Yui.

Objetivos:
- Ter logs estruturados em arquivo para facilitar depuração.
- Não quebrar ambientes onde não for possível criar a pasta de logs.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


_LOGGER: Optional[logging.Logger] = None


def _get_logs_dir() -> str:
    """
    Retorna a pasta de logs.

    - Prioriza a pasta "logs" na raiz do projeto (quando PROJECT_ROOT estiver disponível).
    - Caso contrário, usa a pasta atual.
    """
    try:
        # Import leve, só para descobrir a raiz do projeto.
        from yui_ai.core.file_resolver import PROJECT_ROOT

        base = PROJECT_ROOT
    except Exception:
        base = os.getcwd()

    logs_dir = os.path.join(base, "logs")
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        # Se não conseguir criar, volta para cwd sem subpasta.
        return base
    return logs_dir


def get_logger() -> logging.Logger:
    """
    Retorna um logger singleton da aplicação.
    """
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger("yui")
    logger.setLevel(logging.INFO)

    # Evita adicionar múltiplos handlers ao recarregar módulos.
    if not logger.handlers:
        logs_dir = _get_logs_dir()
        log_path = os.path.join(logs_dir, "yui.log")

        # Handler com rotação (até ~5 MB, 3 arquivos de histórico)
        try:
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)
            fmt = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(fmt)
            logger.addHandler(file_handler)
        except Exception:
            # Em último caso, loga só em stderr.
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            logger.addHandler(stream_handler)

    _LOGGER = logger
    return logger

