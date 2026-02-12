"""
Observer — Consciência operacional.

Registra por turno:
- tempo de execução
- tokens usados
- arquivos alterados
- erros detectados
- impacto no projeto
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_last: Optional["Observation"] = None


@dataclass
class Observation:
    """Snapshot de um turno de execução."""
    turn_start: float = 0.0
    turn_end: float = 0.0
    duration_sec: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tools_executed: List[str] = field(default_factory=list)
    files_altered: List[str] = field(default_factory=list)
    errors_detected: List[str] = field(default_factory=list)
    reply_length: int = 0
    mode: str = "answer"  # answer | tool | tools | skill

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration_sec": round(self.duration_sec, 2),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "tools_executed": self.tools_executed,
            "files_altered": self.files_altered,
            "errors_detected": self.errors_detected,
            "reply_length": self.reply_length,
            "mode": self.mode,
        }


def observe_turn(
    turn_start: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    tools_executed: Optional[List[str]] = None,
    files_altered: Optional[List[str]] = None,
    errors_detected: Optional[List[str]] = None,
    reply_length: int = 0,
    mode: str = "answer",
) -> Observation:
    """Registra observação do turno e retorna o snapshot."""
    global _last
    turn_end = time.time()
    obs = Observation(
        turn_start=turn_start,
        turn_end=turn_end,
        duration_sec=turn_end - turn_start,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        tools_executed=list(tools_executed or []),
        files_altered=list(files_altered or []),
        errors_detected=list(errors_detected or []),
        reply_length=reply_length,
        mode=mode,
    )
    _last = obs
    return obs


def get_last_observation() -> Optional[Observation]:
    """Retorna última observação."""
    return _last
