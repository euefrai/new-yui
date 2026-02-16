import json
import os

# =============================================================
# LOCAL DE DADOS DO USUÁRIO (SEGURO PARA PYINSTALLER)
# =============================================================
APP_NAME = "Yui"

BASE_DATA_DIR = os.path.join(
    os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
    APP_NAME
)

os.makedirs(BASE_DATA_DIR, exist_ok=True)

MEMORY_FILE = os.path.join(BASE_DATA_DIR, "memoria.json")
MAX_MEMORIA_CURTA = 10

# Uma fonte só: Supabase ativo = memória na nuvem; senão = JSON local (evita "cadê minha conversa?").
try:
    from config.settings import USE_LOCAL_MEMORY
except Exception:
    USE_LOCAL_MEMORY = not bool((os.environ.get("SUPABASE_URL") or "").strip())
_MEMORIA_RAM = None  # cache in-memory quando USE_LOCAL_MEMORY é False

# =============================================================
# ESTRUTURA BASE DA MEMÓRIA
# =============================================================
ESTRUTURA_BASE = {
    "preferencias": {},
    "atalhos": {},
    "memoria_curta": [],
    "memoria_longa": [],
    "perfil": {
        "nivel_intimidade": 1,
        "estilo_fala": "neutro",
        "confianca": 1,
        "emoji": False,
        "apelido": None,
        "mensagens": 0
    },
    "projetos": {
        "vexx": {
            "descricao": "",
            "stack": [],
            "decisoes": [],
            "arquitetura": [],
            "maturidade": 1,
            "aprendizados": [],
            "auto_confianca": 1,
            "historico_auto": [],
            "rollback_stack": [],
            "documentacao_viva": {
                "resumo": "",
                "arquitetura": "",
                "decisoes": []
            },
            "roadmap": [],
            "planos": [],
            "feedbacks": [],
            "execucao": {
                "plano_atual": None,
                "etapa_atual": 0
            },
            "autonomia": {
                "nivel": 1,
                "confianca": 0
            },
            "contexto_imediato": {
                "modo": None,
                "confirmado": False,
                "confirmacoes": 0,
                "dados_acao": None
            },
            "execucao_atual": {
                "acao": None,
                "status": None
            },
            "falhas_acao": {}
        }
    }
}

# =============================================================
# CORE: CARREGAR / SALVAR (COM MIGRATION)
# =============================================================
def _garantir_chaves(alvo, base):
    for chave, valor in base.items():
        if chave not in alvo:
            alvo[chave] = valor
        elif isinstance(valor, dict) and isinstance(alvo.get(chave), dict):
            _garantir_chaves(alvo[chave], valor)


def carregar_memoria():
    global _MEMORIA_RAM
    if not USE_LOCAL_MEMORY:
        if _MEMORIA_RAM is None:
            _MEMORIA_RAM = json.loads(json.dumps(ESTRUTURA_BASE))
        return _MEMORIA_RAM

    if not os.path.exists(MEMORY_FILE):
        salvar_memoria(ESTRUTURA_BASE)
        return json.loads(json.dumps(ESTRUTURA_BASE))

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            memoria = json.load(f)
        if not isinstance(memoria, dict):
            raise ValueError("Memória inválida")
    except Exception:
        salvar_memoria(ESTRUTURA_BASE)
        return json.loads(json.dumps(ESTRUTURA_BASE))

    _garantir_chaves(memoria, ESTRUTURA_BASE)
    return memoria


def salvar_memoria(memoria):
    if not USE_LOCAL_MEMORY:
        return
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memoria, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Erro crítico ao salvar memória: {e}")

# =============================================================
# PERFIL / CONVERSA
# =============================================================
def registrar_conversa(texto):
    memoria = carregar_memoria()
    memoria["memoria_curta"].append(texto)
    memoria["memoria_curta"] = memoria["memoria_curta"][-MAX_MEMORIA_CURTA:]
    salvar_memoria(memoria)


def atualizar_perfil():
    memoria = carregar_memoria()
    perfil = memoria["perfil"]
    perfil["mensagens"] += 1

    if perfil["mensagens"] > 10:
        perfil["nivel_intimidade"] = 2
        perfil["emoji"] = True
    if perfil["mensagens"] > 30:
        perfil["estilo_fala"] = "informal"
    if perfil["mensagens"] > 100:
        perfil["confianca"] = 3

    salvar_memoria(memoria)
    return {"status": "ok", "data": perfil}

# =============================================================
# CONTEXTO / EXECUÇÃO
# =============================================================
def set_contexto(modo=None, confirmado=None, dados_acao=None, confirmacoes=None):
    memoria = carregar_memoria()
    ctx = memoria["projetos"]["vexx"]["contexto_imediato"]

    if modo is not None: ctx["modo"] = modo
    if confirmado is not None: ctx["confirmado"] = confirmado
    if dados_acao is not None: ctx["dados_acao"] = dados_acao
    if confirmacoes is not None: ctx["confirmacoes"] = confirmacoes

    salvar_memoria(memoria)


def get_contexto():
    memoria = carregar_memoria()
    return memoria["projetos"]["vexx"]["contexto_imediato"]


def iniciar_execucao_acao(acao):
    memoria = carregar_memoria()
    memoria["projetos"]["vexx"]["execucao_atual"] = {
        "acao": acao,
        "status": "executando"
    }
    salvar_memoria(memoria)


def concluir_execucao():
    memoria = carregar_memoria()
    execucao = memoria["projetos"]["vexx"]["execucao_atual"]
    execucao["status"] = "concluida"
    salvar_memoria(memoria)

# =============================================================
# AUTONOMIA / FALHAS
# =============================================================
def aumentar_autonomia():
    memoria = carregar_memoria()
    autonomia = memoria["projetos"]["vexx"]["autonomia"]

    autonomia["confianca"] += 1
    if autonomia["confianca"] >= 3 and autonomia["nivel"] < 3:
        autonomia["nivel"] += 1
        autonomia["confianca"] = 0

    salvar_memoria(memoria)
    return autonomia


def registrar_falha_acao(acao, erro):
    memoria = carregar_memoria()
    falhas = memoria["projetos"]["vexx"]["falhas_acao"]

    registro = falhas.setdefault(
        acao,
        {"contagem": 0, "ultimo_erro": "", "bloqueado": False}
    )

    registro["contagem"] += 1
    registro["ultimo_erro"] = str(erro)
    if registro["contagem"] >= 3:
        registro["bloqueado"] = True

    salvar_memoria(memoria)


def acao_esta_bloqueada(acao):
    memoria = carregar_memoria()
    registro = memoria["projetos"]["vexx"]["falhas_acao"].get(acao, {})
    return {
        "data": {
            "bloqueado": registro.get("bloqueado", False),
            "tentativas": registro.get("contagem", 0)
        }
    }


def limpar_falha_acao(acao):
    memoria = carregar_memoria()
    memoria["projetos"]["vexx"]["falhas_acao"].pop(acao, None)
    salvar_memoria(memoria)

# =============================================================
# DOCUMENTAÇÃO
# =============================================================
def obter_documentacao_viva():
    memoria = carregar_memoria()
    return memoria["projetos"]["vexx"]["documentacao_viva"]

# =============================================================
# API EXTERNA ESTÁVEL
# =============================================================
def obter_memoria():
    return carregar_memoria()


# =============================================================
# COMPATIBILIDADE (API ANTIGA USADA PELO CORE)
# =============================================================
def obter_autonomia():
    """
    Retorna o bloco de autonomia do projeto.
    Mantido por compatibilidade com `core/autonomy_engine.py`.
    """
    memoria = carregar_memoria()
    return memoria["projetos"]["vexx"].get("autonomia", {"nivel": 1, "confianca": 0})


def obter_erros_acao(acao: str):
    """
    Retorna informações de falhas para uma ação específica.
    Formato esperado por `core/autonomy_engine.py`:
      - falhas (int)
      - bloqueado (bool)
      - ultimo_erro (str)
    """
    if not acao:
        return {"falhas": 0, "bloqueado": False, "ultimo_erro": ""}

    memoria = carregar_memoria()
    registro = memoria["projetos"]["vexx"].get("falhas_acao", {}).get(acao, {})
    return {
        "falhas": int(registro.get("contagem", 0) or 0),
        "bloqueado": bool(registro.get("bloqueado", False)),
        "ultimo_erro": str(registro.get("ultimo_erro", "") or "")
    }
