import os
import json
import hashlib
from dotenv import load_dotenv

import re

from yui_ai.memory.memory import obter_memoria
from yui_ai.config.config import SYSTEM_PROMPT, SYSTEM_PROMPT_ANALISE_CODIGO

# Import tardio para evitar ciclo (code_generator importa ai_engine)
def _build_context_chat():
    from yui_ai.ai.context_builder import build_context
    return build_context()

# =============================================================
# AMBIENTE
# =============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
# Local: carrega .env se existir. Render: não usa .env — variáveis vêm de os.environ.
_env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.isfile(_env_path):
    load_dotenv(_env_path)

# Chave sempre lida de os.environ (Render injeta aqui; local pode ter vindo do .env acima).
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()

try:
    from openai import OpenAI  # import tardio e opcional
except Exception:  # noqa: BLE001
    OpenAI = None

# Cliente criado com a chave explícita; no Render não existe .env, só os.environ.
client = OpenAI(api_key=OPENAI_API_KEY) if (OpenAI and OPENAI_API_KEY) else None

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
# DETECÇÃO DE CÓDIGO (MODO ANALISADOR)
# =============================================================
def detectar_codigo(mensagem: str) -> bool:
    """Ativa MODO_ANALISE_CODIGO se a mensagem parecer trecho de código."""
    if not mensagem or len(mensagem.strip()) < 20:
        return False
    msg = mensagem.strip()
    # Extensões no texto
    if re.search(r"\b\.(py|js|ts|jsx|tsx|css|html|json|yml|yaml)\b", msg, re.I):
        return True
    # Chaves de código
    if "{" in msg and "}" in msg and msg.count("{") >= 1:
        return True
    # Tags HTML
    if re.search(r"</?[a-z][a-z0-9]*[\s>]", msg, re.I):
        return True
    # Palavras-chave de linguagens
    if re.search(r"\b(function|const|let|var|import|from|def|class|=>)\b", msg):
        return True
    # Indentação típica (múltiplas linhas começando com espaços)
    linhas = [l for l in msg.splitlines() if l.strip()]
    if len(linhas) >= 2 and sum(1 for l in linhas if re.match(r"^[\s]+", l)) >= 2:
        return True
    return False


# =============================================================
# MOTOR DE IA
# =============================================================
def perguntar_yui(mensagem, intencao=None):
    # Ações não passam pelo chat
    if intencao and intencao.get("tipo") in ["acao", "sistema", "controle"]:
        return None

    if client is None:
        return {
            "status": "error",
            "api_key_missing": True,
            "data": {
                "resposta": "⚠️ Configuração necessária\n\nA chave da OpenAI não foi detectada no servidor.\nConfigure a variável OPENAI_API_KEY no ambiente de deploy (ex.: Render → Environment).",
                "acao": "nenhuma",
                "dados": {},
                "nivel": 0
            }
        }

    modo_analise = detectar_codigo(mensagem)
    system_prompt = SYSTEM_PROMPT_ANALISE_CODIGO if modo_analise else SYSTEM_PROMPT
    user_content = mensagem
    if modo_analise:
        user_content = "Analise o código abaixo e responda no formato obrigatório (🧠 O que faz / ⚠️ Problemas / 💡 Como melhorar / 🚀 Versão melhorada).\n\n" + mensagem
    else:
        # Contexto das últimas 8 mensagens do chat (memória persistente)
        ctx_chat = _build_context_chat()
        if ctx_chat:
            user_content = ctx_chat + "Usuário: " + mensagem

    mensagens = [
        {"role": "system", "content": system_prompt},
    ]

    ctx_vexx = montar_contexto_vexx()
    ctx_mem = montar_contexto_memoria()

    if ctx_vexx:
        mensagens.append({"role": "system", "content": ctx_vexx})
    if ctx_mem:
        mensagens.append({"role": "system", "content": ctx_mem})

    mensagens.append({"role": "user", "content": user_content})

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


# =============================================================
# GERAÇÃO DE CÓDIGO (para ai/code_generator)
# =============================================================
SYSTEM_PROMPT_GERAR_CODIGO = """Você é a Yui, assistente autônoma de código. O usuário pediu para gerar código.

Regras:
- Gere código COMPLETO e que rode (não pseudocódigo).
- Use a linguagem pedida (Java, JavaScript, Python, HTML, CSS). Não troque em silêncio.
- Se fizer sentido, sugira alternativa (ex.: "versão web em JS") e explique.
- Estrutura limpa, modular, nomes claros.
- Responda em português (Brasil), texto puro (não use JSON).

Formato da resposta:

📦 Título curto do que foi criado

🧠 Explicação curta
(uma ou duas frases em linguagem clara)

💻 Código
(bloco completo e funcional na linguagem pedida)

⚙️ Melhorias possíveis
- item 1
- item 2 (opcional)

NUNCA execute código — apenas mostre como texto. Não gere malware nem scripts prejudiciais."""


def _gerar_resposta_codigo_ia(pedido: str, linguagem: str):
    """
    Chama a IA para gerar código conforme pedido e linguagem.
    Retorna (sucesso: bool, texto: str, erro: Optional[str]).
    """
    if client is None:
        return False, "", "OPENAI_API_KEY não configurada."

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_GERAR_CODIGO},
                {"role": "user", "content": f"Linguagem: {linguagem}. Pedido do usuário: {pedido}"},
            ],
            temperature=0.5,
        )
        texto = (response.choices[0].message.content or "").strip()
        return True, texto, None
    except Exception as e:
        return False, "", str(e)
