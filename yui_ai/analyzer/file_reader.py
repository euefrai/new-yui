"""Leitura segura de arquivo (bytes). UTF-8 com fallback. NUNCA executa."""
from typing import Optional, Tuple

MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1 MB


def read_file_safe(content: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Decodifica conteúdo de forma segura. Retorna (texto, None) ou (None, erro)."""
    if not content:
        return None, "Arquivo vazio."
    if len(content) > MAX_FILE_SIZE_BYTES:
        return None, f"Arquivo muito grande (máximo {MAX_FILE_SIZE_BYTES // 1024} KB)."
    try:
        return content.decode("utf-8"), None
    except UnicodeDecodeError:
        pass
    try:
        return content.decode("latin-1"), None
    except Exception as e:
        return None, f"Não foi possível decodificar: {e}"
