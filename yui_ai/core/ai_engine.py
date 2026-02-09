import os
import json
import hashlib
from dotenv import load_dotenv

from yui_ai.memory.memory import obter_memoria
from yui_ai.config.config import SYSTEM_PROMPT

# =============================================================
# AMBIENTE
# =============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
# Prioriza variáveis de ambiente, mas também suporta um ".env" no root do projeto.
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# OpenAI é opcional: se não estiver instalado/configurado, a Yui continua funcionando (sem IA).
try:
    from openai import OpenAI  # import tardio e opcional
except Exception:  # noqa: BLE001
    OpenAI = None

_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=_api_key) if (OpenAI and _api_key) else None

CACHE_IA = {}

# =============================================================
# CONTEXTO
# =============================================================
def montar_contexto_memoria():
    memoria = obter_memoria()
    mem_curta = memoria.get("memoria_curta", [])

    if not mem_curta:
        return ""

    return "Últimas interações:\n" + " | ".join(mem_curta[-5:])


def montar_contexto_vexx():
    memoria = obter_memoria()
    vexx = memoria.get("projetos", {}).get("vexx", {})
    if not vexx:
        return ""

    texto = "Projeto VEXX:\n"
    for k in ["stack", "decisoes", "arquitetura"]:
        itens = vexx.get(k, [])
        if itens:
            texto += f"- {k}: {', '.join(itens[-3:])}\n"

    return texto.strip()

# =============================================================
# PARSER SEGURO DE JSON
# =============================================================
def _parse_json_resposta(texto):
    try:
        inicio = texto.find("{")
        fim = texto.rfind("}") + 1
        if inicio == -1 or fim == -1:
            raise ValueError("JSON não encontrado")
        return json.loads(texto[inicio:fim])
    except Exception:
        return {
            "resposta": texto.strip(),
            "acao": "nenhuma",
            "dados": {},
            "nivel": 0
        }

# =============================================================
# MOTOR DE IA
# =============================================================
def perguntar_yui(mensagem, intencao=None):
    # Ações não passam pelo chat
    if intencao and intencao.get("tipo") in ["acao", "sistema", "controle"]:
        return None

    if client is None:
        return {
            "status": "ok",
            "data": {
                "resposta": "Eu consigo conversar melhor quando você configura a variável OPENAI_API_KEY (arquivo .env).",
                "acao": "nenhuma",
                "dados": {},
                "nivel": 0
            }
        }

    mensagens = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    ctx_vexx = montar_contexto_vexx()
    ctx_mem = montar_contexto_memoria()

    if ctx_vexx:
        mensagens.append({"role": "system", "content": ctx_vexx})
    if ctx_mem:
        mensagens.append({"role": "system", "content": ctx_mem})

    mensagens.append({"role": "user", "content": mensagem})

    cache_key = hashlib.md5(str(mensagens).encode()).hexdigest()
    if cache_key in CACHE_IA:
        return CACHE_IA[cache_key]

    try:
        # Usa chat.completions.create (API padrão da OpenAI)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=mensagens,
            temperature=0.6
        )

        texto = response.choices[0].message.content.strip()
        payload = _parse_json_resposta(texto)

        resultado = {
            "status": "ok",
            "data": payload
        }

        CACHE_IA[cache_key] = resultado
        return resultado

    except Exception as e:
        return {
            "status": "error",
            "data": {
                "resposta": "Tive um probleminha aqui 😕",
                "acao": "nenhuma",
                "dados": {},
                "nivel": 0,
                "erro": str(e)
            }
        }
