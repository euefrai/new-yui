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
OPENAI_MODEL = _get("OPENAI_MODEL") or "gpt-4o-mini"

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

# Memória: uma fonte só — USE_SUPABASE_MEMORY=true usa cloud; false usa JSON local
_use_supabase_env = os.environ.get("USE_SUPABASE_MEMORY", "").strip().lower() in ("1", "true", "yes")
USE_SUPABASE_MEMORY = _use_supabase_env or bool(SUPABASE_URL and SUPABASE_KEY_BACKEND)
USE_LOCAL_MEMORY = not USE_SUPABASE_MEMORY

# Pastas derivadas
GENERATED_PROJECTS_DIR = BASE_DIR / "generated_projects"
WEB_LEGACY_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"
SANDBOX_DIR = BASE_DIR / "sandbox"
