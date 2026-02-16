"""
Memória de Erros (Lessons Learned) — .yui_lessons.md
Grava correções do usuário para a IA não repetir.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from config import settings
    SANDBOX_DIR = Path(settings.SANDBOX_DIR).resolve()
except Exception:
    SANDBOX_DIR = Path(__file__).resolve().parents[1] / "sandbox"

LESSONS_FILE = ".yui_lessons.md"


def _get_lessons_path(root: Optional[Path] = None) -> Path:
    return (root or SANDBOX_DIR) / LESSONS_FILE


def append_lesson(
    error_context: str,
    correction: str,
    root: Optional[Path] = None,
) -> bool:
    """
    Adiciona uma lição aprendida ao .yui_lessons.md.
    error_context: o que a IA fez errado
    correction: como o usuário corrigiu
    """
    path = _get_lessons_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {now}\n\n**Erro:** {error_context[:500]}\n\n**Correção:** {correction[:500]}\n\n---\n"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception:
        return False


def read_lessons(root: Optional[Path] = None) -> str:
    """Lê o conteúdo de .yui_lessons.md para incluir no contexto."""
    path = _get_lessons_path(root)
    if not path.is_file():
        return ""
    try:
        content = path.read_text(encoding="utf-8")
        return content[-8000:] if len(content) > 8000 else content
    except Exception:
        return ""
