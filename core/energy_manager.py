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
    ENERGY_MAX = float(getattr(settings, "ENERGY_MAX", 180))
    ENERGY_LOW_THRESHOLD = float(getattr(settings, "ENERGY_LOW_THRESHOLD", max(20, int(ENERGY_MAX * 0.2))))
    ENERGY_CRITICAL_THRESHOLD = float(getattr(settings, "ENERGY_CRITICAL_THRESHOLD", max(10, int(ENERGY_MAX * 0.1))))
    ENERGY_MIN_BOOT = float(getattr(settings, "ENERGY_MIN_BOOT", max(30, int(ENERGY_MAX * 0.25))))
    COST_RESPONDER_IA = float(getattr(settings, "ENERGY_COST_RESPONDER_IA", 8))
    COST_TOOL = float(getattr(settings, "ENERGY_COST_TOOL", 10))
    COST_PLANNER = float(getattr(settings, "ENERGY_COST_PLANNER", 3))
    COST_REFLECT = float(getattr(settings, "ENERGY_COST_REFLECT", 2))
    COST_RECOVERY = float(getattr(settings, "ENERGY_COST_RECOVERY", 10))
except Exception:
    ENERGY_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "energy_state.json"
    ENERGY_MAX = 180.0
    ENERGY_LOW_THRESHOLD = max(20.0, ENERGY_MAX * 0.2)
    ENERGY_CRITICAL_THRESHOLD = max(10.0, ENERGY_MAX * 0.1)
    ENERGY_MIN_BOOT = max(30.0, ENERGY_MAX * 0.25)
    COST_RESPONDER_IA = 8.0
    COST_TOOL = 10.0
    COST_PLANNER = 3.0
    COST_REFLECT = 2.0
    COST_RECOVERY = 10.0

# Custos por tipo de ação (configuráveis via settings/.env)


def _load_state() -> dict:
    """Carrega estado de energia do disco."""
    ENERGY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENERGY_STATE_PATH.exists():
        return {"energy": ENERGY_MAX, "last_updated": ""}
    try:
        with open(ENERGY_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"energy": ENERGY_MAX, "last_updated": ""}


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
        loaded = float(state.get("energy", ENERGY_MAX))
        # Evita ficar preso para sempre em 0 energia entre sessões.
        # Se iniciar muito baixo, sobe para um piso operacional seguro.
        self.energy = max(ENERGY_MIN_BOOT, min(ENERGY_MAX, loaded))
        self._state_path = ENERGY_STATE_PATH
        if self.energy != loaded:
            _save_state({"energy": self.energy})

    def consume(self, amount: float) -> None:
        """Consome energia. Não persiste a cada consume para performance."""
        self.energy = max(0, self.energy - amount)

    def can_execute(self) -> bool:
        """Verifica se ainda há energia para executar."""
        return self.energy > 0

    def is_low(self) -> bool:
        """Energia baixa: planner deve criar plano simples."""
        return self.energy < ENERGY_LOW_THRESHOLD

    def is_critical(self) -> bool:
        """Energia crítica: responder versão resumida."""
        return self.energy < ENERGY_CRITICAL_THRESHOLD

    def recover(self, amount: Optional[float] = None) -> None:
        """Recupera energia após resposta. Persiste no disco."""
        amt = amount if amount is not None else COST_RECOVERY
        self.energy = min(ENERGY_MAX, self.energy + amt)
        _save_state({"energy": self.energy})

    def persist(self) -> None:
        """Persiste estado atual (útil ao final do turno)."""
        _save_state({"energy": self.energy})

    def reset(self) -> None:
        """Reseta para o máximo configurado (útil em testes)."""
        self.energy = ENERGY_MAX
        _save_state({"energy": ENERGY_MAX})


# Singleton global (uma instância por processo)
_energy_manager: Optional[EnergyManager] = None


def get_energy_manager() -> EnergyManager:
    """Retorna instância global do EnergyManager."""
    global _energy_manager
    if _energy_manager is None:
        _energy_manager = EnergyManager()
    return _energy_manager
