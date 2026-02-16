"""
Action Engine — O coração da Yui.

Decide quando:
- abrir editor
- executar código
- usar terminal
- chamar analyzer
- fazer RAG

Conecta a IA ao orquestrador real (não mais UI + scripts dispersos).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionIntent:
    """Intenção decodificada: qual ação o sistema deve tomar."""
    action: str  # open_editor | execute_code | use_terminal | call_analyzer | rag | answer
    confidence: float = 0.0
    params: Dict[str, Any] = field(default_factory=dict)
    tool_hint: Optional[str] = None  # ferramenta sugerida (ex: analisar_projeto)
    reason: str = ""


# Palavras-chave que disparam cada ação
_OPEN_EDITOR_SIGNALS = [
    "editar", "abrir arquivo", "mostrar código", "ver arquivo", "modificar",
    "alterar", "criar arquivo", "escrever em", "adicionar em",
]
_EXECUTE_SIGNALS = [
    "executar", "rodar", "run", "testar", "rodar código", "executar código",
    "▶", "play", "run script",
]
_TERMINAL_SIGNALS = [
    "terminal", "comando", "cmd", "bash", "npm", "pip install", "git ",
    "instalar", "console", "prompt",
]
_ANALYZER_SIGNALS = [
    "analisar", "analise", "arquitetura", "riscos", "roadmap", "dependências",
    "qualidade", "revisar código", "code review", "lint",
]
_RAG_SIGNALS = [
    "lembrar", "memória", "decisão anterior", "o que fizemos", "histórico",
    "conclusão", "resumo do projeto",
]


def _score_signals(text: str, signals: List[str]) -> float:
    """Score 0-1 baseado em matches nos sinais."""
    if not text or not signals:
        return 0.0
    lower = text.lower().strip()
    matches = sum(1 for s in signals if s.lower() in lower)
    return min(1.0, matches * 0.4) if matches else 0.0


def route_action(
    user_message: str,
    last_tool: Optional[str] = None,
    active_files: Optional[List[str]] = None,
    has_console_errors: bool = False,
) -> ActionIntent:
    """
    Roteia a intenção do usuário para uma ação do sistema.

    Args:
        user_message: mensagem do usuário
        last_tool: última ferramenta executada (contexto)
        active_files: arquivos abertos no workspace
        has_console_errors: se há erros no console

    Returns:
        ActionIntent com action, confidence, params
    """
    msg = (user_message or "").strip()
    scores: Dict[str, float] = {}

    scores["open_editor"] = _score_signals(msg, _OPEN_EDITOR_SIGNALS)
    scores["execute_code"] = _score_signals(msg, _EXECUTE_SIGNALS)
    scores["use_terminal"] = _score_signals(msg, _TERMINAL_SIGNALS)
    scores["call_analyzer"] = _score_signals(msg, _ANALYZER_SIGNALS)
    scores["rag"] = _score_signals(msg, _RAG_SIGNALS)

    # Boost por contexto
    if has_console_errors and any(w in msg.lower() for w in ("erro", "error", "corrigir", "fix")):
        scores["open_editor"] = max(scores.get("open_editor", 0), 0.6)
    if last_tool == "analisar_projeto" and "detalhe" in msg.lower():
        scores["call_analyzer"] = max(scores.get("call_analyzer", 0), 0.5)

    best = max(scores, key=lambda k: scores[k])
    conf = scores[best]

    # Mapeamento action -> tool_hint
    tool_map = {
        "open_editor": "fs_create_file",
        "execute_code": None,  # execução via UI (Run no workspace)
        "use_terminal": None,  # terminal é via WebSocket, não tool
        "call_analyzer": "analisar_projeto",
        "rag": None,  # memoria_ia já está no contexto
    }

    return ActionIntent(
        action=best if conf > 0.2 else "answer",
        confidence=conf,
        params={"user_message": msg},
        tool_hint=tool_map.get(best) if conf > 0.2 else None,
        reason=f"Score: {best}={conf:.2f}",
    )
