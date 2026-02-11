# ==========================================================
# YUI ENERGY MANAGER
# Freio cognitivo: evita loops infinitos, picos de RAM e SIGKILL.
# Cada ação tem custo; energia recupera após resposta.
# ==========================================================

import json
from pathlib import Path
from typing import Optional

try:
    from config import settings
    ENERGY_STATE_PATH = Path(settings.DATA_DIR) / "energy_state.json"
except Exception:
    ENERGY_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "energy_state.json"

# Custos por tipo de ação
COST_RESPONDER_IA = 10   # chamada à IA para resposta
COST_TOOL = 15           # execução de uma tool
COST_PLANNER = 5         # criar/avaliar plano
COST_REFLECT = 3         # reflexão (self_reflect, auto_debug)
COST_RECOVERY = 5        # ganho após responder


def _load_state() -> dict:
    """Carrega estado de energia do disco."""
    ENERGY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENERGY_STATE_PATH.exists():
        return {"energy": 100, "last_updated": ""}
    try:
        with open(ENERGY_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"energy": 100, "last_updated": ""}


def _save_state(data: dict) -> None:
    """Salva estado de energia."""
    import datetime
    ENERGY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.datetime.utcnow().isoformat()
    with open(ENERGY_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class EnergyManager:
    """
    Gerenciador de energia mental da Yui.
    Global (por servidor): protege RAM e evita runaway.
    """

    def __init__(self):
        state = _load_state()
        self.energy = float(state.get("energy", 100))
        self._state_path = ENERGY_STATE_PATH

    def consume(self, amount: float) -> None:
        """Consome energia. Não persiste a cada consume para performance."""
        self.energy = max(0, self.energy - amount)

    def can_execute(self) -> bool:
        """Verifica se ainda há energia para executar."""
        return self.energy > 0

    def is_low(self) -> bool:
        """Energia baixa: planner deve criar plano simples."""
        return self.energy < 20

    def is_critical(self) -> bool:
        """Energia crítica: responder versão resumida."""
        return self.energy < 10

    def recover(self, amount: Optional[float] = None) -> None:
        """Recupera energia após resposta. Persiste no disco."""
        amt = amount if amount is not None else COST_RECOVERY
        self.energy = min(100, self.energy + amt)
        _save_state({"energy": self.energy})

    def persist(self) -> None:
        """Persiste estado atual (útil ao final do turno)."""
        _save_state({"energy": self.energy})

    def reset(self) -> None:
        """Reseta para 100 (útil em testes)."""
        self.energy = 100
        _save_state({"energy": 100})


# Singleton global (uma instância por processo)
_energy_manager: Optional[EnergyManager] = None


def get_energy_manager() -> EnergyManager:
    """Retorna instância global do EnergyManager."""
    global _energy_manager
    if _energy_manager is None:
        _energy_manager = EnergyManager()
    return _energy_manager
