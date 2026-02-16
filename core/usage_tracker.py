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

# Preços OpenAI gpt-4o-mini (US$/1M tokens) - baseado em faturamento ~US$20 Cursor
PRICE_INPUT_PER_1M = 0.15
PRICE_OUTPUT_PER_1M = 0.60
CHARS_PER_TOKEN = 4
BRL_PER_USD = 5.0  # Cotação BRL/USD (ajustável)
BUDGET_ALERT_BRL = 0.20

_last_response_cost_brl: float = 0.0
_last_response_tokens: dict = {}

# Custo por escrita em disco (Zeabur: monitorar uso)
COST_DISK_WRITE_BRL = 0.001  # R$ por operação de escrita (ajustável)


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


def record_disk_write() -> None:
    """Registra escrita em disco para auditoria de custo Zeabur."""
    today = date.today().isoformat()
    data = _load_usage()
    day_data = data.get(today, {"energy_consumed": 0, "requests": 0, "token_cost_brl": 0, "disk_writes": 0, "disk_write_cost_brl": 0})
    day_data["disk_writes"] = day_data.get("disk_writes", 0) + 1
    day_data["disk_write_cost_brl"] = day_data.get("disk_write_cost_brl", 0) + COST_DISK_WRITE_BRL
    data[today] = day_data
    _save_usage(data)


def record_consumption(energy_consumed: float) -> None:
    """Registra consumo de energia do dia."""
    today = date.today().isoformat()
    data = _load_usage()
    day_data = data.get(today, {"energy_consumed": 0, "requests": 0, "token_cost_brl": 0, "disk_writes": 0, "disk_write_cost_brl": 0})
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
    day_data = data.get(today, {"energy_consumed": 0, "requests": 0, "token_cost_brl": 0, "disk_writes": 0, "disk_write_cost_brl": 0})
    token_cost = day_data.get("token_cost_brl", 0)
    disk_cost = day_data.get("disk_write_cost_brl", 0)
    energy_cost = day_data.get("energy_consumed", 0) * COST_PER_ENERGY_UNIT
    # Preferir custo por token (auditoria real) quando disponível
    cost = token_cost if token_cost > 0 else energy_cost
    cost = round(cost + disk_cost, 2)
    return {
        "energy_consumed": day_data.get("energy_consumed", 0),
        "requests": day_data.get("requests", 0),
        "cost_estimate": cost,
        "disk_writes": day_data.get("disk_writes", 0),
        "disk_write_cost_brl": round(day_data.get("disk_write_cost_brl", 0), 4),
        "last_response_cost": round(_last_response_cost_brl, 4),
        "last_response_tokens": _last_response_tokens,
    }


def estimate_cost_brl(prompt_chars: int, estimated_output_chars: int = 4000) -> float:
    """Estima custo em R$ baseado em chars (≈4 chars/token)."""
    inp_tokens = max(0, prompt_chars) // CHARS_PER_TOKEN
    out_tokens = max(0, estimated_output_chars) // CHARS_PER_TOKEN
    usd = (inp_tokens * PRICE_INPUT_PER_1M / 1_000_000) + (out_tokens * PRICE_OUTPUT_PER_1M / 1_000_000)
    return round(usd * BRL_PER_USD, 4)


def record_response_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Registra custo da última resposta e retorna valor em R$."""
    global _last_response_cost_brl, _last_response_tokens
    usd = (prompt_tokens * PRICE_INPUT_PER_1M / 1_000_000) + (completion_tokens * PRICE_OUTPUT_PER_1M / 1_000_000)
    _last_response_cost_brl = round(usd * BRL_PER_USD, 4)
    _last_response_tokens = {"prompt": prompt_tokens, "completion": completion_tokens}
    # Acumular custo por token no dia (auditoria)
    today = date.today().isoformat()
    data = _load_usage()
    day_data = data.get(today, {"energy_consumed": 0, "requests": 0, "token_cost_brl": 0})
    day_data["token_cost_brl"] = day_data.get("token_cost_brl", 0) + _last_response_cost_brl
    data[today] = day_data
    _save_usage(data)
    return _last_response_cost_brl


def get_last_response_cost() -> float:
    return _last_response_cost_brl
