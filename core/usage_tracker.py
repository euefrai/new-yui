# ==========================================================
# YUI USAGE TRACKER
# Custo acumulado por dia (energia consumida como proxy).
# Transparência para o usuário do SaaS.
# ==========================================================

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict

try:
    from config import settings
    USAGE_PATH = Path(settings.DATA_DIR) / "usage_daily.json"
except Exception:
    USAGE_PATH = Path(__file__).resolve().parents[1] / "data" / "usage_daily.json"

# Custo por unidade (arbitrário, para exibição; ajuste conforme seu modelo de faturamento)
COST_PER_ENERGY_UNIT = 0.01  # ex: R$ 0,01 por unidade de energia


def _load_usage() -> Dict[str, Any]:
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not USAGE_PATH.exists():
        return {}
    try:
        with open(USAGE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_usage(data: Dict[str, Any]) -> None:
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_consumption(energy_consumed: float) -> None:
    """Registra consumo de energia do dia."""
    today = date.today().isoformat()
    data = _load_usage()
    day_data = data.get(today, {"energy_consumed": 0, "requests": 0})
    day_data["energy_consumed"] = day_data.get("energy_consumed", 0) + energy_consumed
    day_data["requests"] = day_data.get("requests", 0) + 1
    data[today] = day_data
    # Mantém últimos 30 dias
    keys = sorted(data.keys(), reverse=True)[:30]
    data = {k: data[k] for k in keys}
    _save_usage(data)


def get_today_usage() -> Dict[str, Any]:
    """Retorna uso do dia atual."""
    today = date.today().isoformat()
    data = _load_usage()
    day_data = data.get(today, {"energy_consumed": 0, "requests": 0})
    cost = day_data.get("energy_consumed", 0) * COST_PER_ENERGY_UNIT
    return {
        "energy_consumed": day_data.get("energy_consumed", 0),
        "requests": day_data.get("requests", 0),
        "cost_estimate": round(cost, 2),
    }
