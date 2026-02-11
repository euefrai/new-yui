"""
Memória de Erros (Lessons Learned): .yui_lessons.md
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
LESSONS_HEADER = """# Lessons Learned — Yui

Correções aplicadas pelo usuário. **Nunca repita estes erros.**

"""


def _lessons_path(root: Optional[Path] = None) -> Path:
    return (root or SANDBOX_DIR) / LESSONS_FILE


def read_lessons(root: Optional[Path] = None) -> str:
    """Lê conteúdo de .yui_lessons.md."""
    path = _lessons_path(root)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def append_lesson(
    error_description: str,
    correction: str,
    context: Optional[str] = None,
    root: Optional[Path] = None,
) -> bool:
    """
    Adiciona uma correção ao .yui_lessons.md.
    error_description: o que estava errado
    correction: como foi corrigido
    context: contexto opcional (ex: código que gerou o erro)
    """
    if not error_description or not correction:
        return False
    path = _lessons_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    entry = f"""
## {now}

**Erro:** {error_description.strip()}

**Correção:** {correction.strip()}
"""
    if context:
        entry += f"\n**Contexto:**\n```\n{context.strip()[:500]}\n```\n"
    entry += "\n---\n"
    try:
        if not path.exists():
            path.write_text(LESSONS_HEADER + entry, encoding="utf-8")
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry)
        return True
    except Exception:
        return False


def get_lessons_for_prompt(root: Optional[Path] = None, max_chars: int = 2000) -> str:
    """Retorna lessons formatadas para incluir no prompt (últimas entradas)."""
    raw = read_lessons(root)
    if not raw:
        return ""
    lines = raw.split("\n")
    if len(lines) <= 3:
        return ""
    content = "\n".join(lines).strip()
    if len(content) > max_chars:
        content = "...\n\n" + content[-max_chars:]
    return (
        "LESSONS LEARNED (correções do usuário — NUNCA repita estes erros):\n\n"
        + content
        + "\n\n---\n"
    )
