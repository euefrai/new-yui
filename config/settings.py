"""
Configuração centralizada: variáveis de ambiente e constantes.
Evita ler .env espalhado e deixa uma única fonte (BASE_DIR, keys, etc.).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto (onde estão web_server.py, cli.py)
BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_PATH = BASE_DIR / ".env"
if _ENV_PATH.is_file():
    load_dotenv(_ENV_PATH)


def _get(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()


# OpenAI
OPENAI_API_KEY = _get("OPENAI_API_KEY")
OPENAI_MODEL = _get("OPENAI_MODEL") or "gpt-5-mini"

# Supabase — duas keys: anon no frontend, service_role no backend
SUPABASE_URL = _get("SUPABASE_URL")
SUPABASE_ANON_KEY = (
    _get("SUPABASE_ANON_KEY")
    or _get("SUPABASE_PUBLISHABLE_KEY")
    or _get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY")
    or _get("SUPABASE_KEY")  # fallback: Zeabur pode usar SUPABASE_KEY como anon
)
SUPABASE_SERVICE_KEY = _get("SUPABASE_SERVICE_KEY") or _get("SUPABASE_SERVICE_ROLE_KEY") or _get("SUPABASE_KEY")

# Backend usa sempre service_role (nunca expor no frontend)
SUPABASE_KEY_BACKEND = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY

# Flask
SECRET_KEY = _get("SECRET_KEY") or "yui-dev-secret-change-in-production"
PORT = int(os.environ.get("PORT") or "5000")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
USE_MINIFIED_STATIC = os.environ.get("USE_MINIFIED_STATIC", "false").lower() in ("1", "true", "yes")
STATIC_VERSION = _get("STATIC_VERSION") or "20260215"

# Async: USE_ASYNC_QUEUE=true habilita POST /send?async=1 → job_id (poll GET /chat/job/<id>)
USE_ASYNC_QUEUE = os.environ.get("USE_ASYNC_QUEUE", "").lower() in ("1", "true", "yes")

# Memória: uma fonte só — USE_SUPABASE_MEMORY=true usa cloud; false usa JSON local
_use_supabase_env = os.environ.get("USE_SUPABASE_MEMORY", "").strip().lower() in ("1", "true", "yes")
USE_SUPABASE_MEMORY = _use_supabase_env or bool(SUPABASE_URL and SUPABASE_KEY_BACKEND)
USE_LOCAL_MEMORY = not USE_SUPABASE_MEMORY

# Energy Manager (freio cognitivo)
ENERGY_MAX = int(os.environ.get("ENERGY_MAX") or "180")
ENERGY_LOW_THRESHOLD = int(os.environ.get("ENERGY_LOW_THRESHOLD") or str(max(20, int(ENERGY_MAX * 0.2))))
ENERGY_CRITICAL_THRESHOLD = int(os.environ.get("ENERGY_CRITICAL_THRESHOLD") or str(max(10, int(ENERGY_MAX * 0.1))))
ENERGY_MIN_BOOT = int(os.environ.get("ENERGY_MIN_BOOT") or str(max(30, int(ENERGY_MAX * 0.25))))
ENERGY_COST_RESPONDER_IA = float(os.environ.get("ENERGY_COST_RESPONDER_IA") or "8")
ENERGY_COST_TOOL = float(os.environ.get("ENERGY_COST_TOOL") or "10")
ENERGY_COST_PLANNER = float(os.environ.get("ENERGY_COST_PLANNER") or "3")
ENERGY_COST_REFLECT = float(os.environ.get("ENERGY_COST_REFLECT") or "2")
ENERGY_COST_RECOVERY = float(os.environ.get("ENERGY_COST_RECOVERY") or "10")

# Pastas derivadas
GENERATED_PROJECTS_DIR = BASE_DIR / "generated_projects"
WEB_LEGACY_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"
SANDBOX_DIR = BASE_DIR / "sandbox"
