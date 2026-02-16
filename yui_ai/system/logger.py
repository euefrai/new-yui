"""Logging centralizado. Salva em %LOCALAPPDATA%/Yui/logs/yui.log. Formato: [DATA][INFO/ERROR] msg."""
import logging
import os
from typing import Any, Optional

_LOGGER: Optional[logging.Logger] = None


def _get_log_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    log_dir = os.path.join(base, "Yui", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        pass
    return log_dir


def _get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    log_dir = _get_log_dir()
    log_path = os.path.join(log_dir, "yui.log")
    logger = logging.getLogger("yui")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        try:
            fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setLevel(logging.INFO)
            fh.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            logger.addHandler(fh)
        except Exception:
            sh = logging.StreamHandler()
            sh.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            logger.addHandler(sh)
    _LOGGER = logger
    return logger


def log_event(mensagem: str, contexto: Optional[Any] = None) -> None:
    logger = _get_logger()
    if contexto is not None:
        mensagem = f"{mensagem} | {contexto}"
    logger.info(mensagem)


def log_error(erro: BaseException, contexto: Optional[Any] = None) -> None:
    logger = _get_logger()
    msg = str(erro) if erro else "Erro desconhecido"
    if contexto is not None:
        msg = f"{msg} | {contexto}"
    logger.error(msg, exc_info=True)
