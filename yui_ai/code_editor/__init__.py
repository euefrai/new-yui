"""
Engine de edição de código baseado em diff/patch.

Nunca reescreve arquivos inteiros - sempre usa diffs unificados.
"""

from yui_ai.code_editor.diff_engine import gerar_diff, aplicar_diff
from yui_ai.code_editor.patch_engine import PatchEngine
from yui_ai.code_editor.file_manager import FileManager
from yui_ai.code_editor.history_manager import HistoryManager

__all__ = [
    "gerar_diff",
    "aplicar_diff",
    "PatchEngine",
    "FileManager",
    "HistoryManager"
]
