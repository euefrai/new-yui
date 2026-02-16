"""
Cliente Supabase: duas keys — anon (frontend) e service (backend).
Nunca expor SERVICE_KEY em templates ou JS.
"""
from typing import Literal, Optional

from config import settings

_anon_client = None
_service_client = None


def get_supabase_client(mode: Literal["anon", "service"] = "anon"):
    """
    Retorna o cliente Supabase para o modo pedido.
    - mode="anon": chave pública (frontend, login/Auth).
    - mode="service": chave service_role (backend, operações administrativas).
    """
    global _anon_client, _service_client
    if not settings.SUPABASE_URL:
        return None
    if mode == "service":
        key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_ANON_KEY
        if not key:
            return None
        if _service_client is None:
            try:
                from supabase import create_client
                _service_client = create_client(settings.SUPABASE_URL, key)
            except Exception:
                _service_client = None
        return _service_client
    else:
        key = settings.SUPABASE_ANON_KEY
        if not key:
            return None
        if _anon_client is None:
            try:
                from supabase import create_client
                _anon_client = create_client(settings.SUPABASE_URL, key)
            except Exception:
                _anon_client = None
        return _anon_client


# Backend usa sempre service (compatibilidade com código que importa supabase)
supabase = get_supabase_client("service")
