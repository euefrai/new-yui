# ==========================================================
# YUI FAIL SAFE (v2)
# Limites para evitar travamento (ex: out of memory no Render).
# Agentes sem limites travam servidor.
# ==========================================================

import os

# Máximo de etapas no plano (planner respeita isso)
MAX_STEPS = int(os.environ.get("YUI_MAX_STEPS", "5"))

# Máximo de tokens na resposta (placeholder; modelo tem seu próprio limite)
MAX_TOKENS = int(os.environ.get("YUI_MAX_TOKENS", "4096"))

# Timeout em segundos por execução de tool (placeholder para futuro)
TIMEOUT_SECONDS = int(os.environ.get("YUI_TIMEOUT", "30"))
