from yui_ai.memory.memory import registrar_falha_acao
from yui_ai.autocorrection_engine import (
    buscar_solucao,
    salvar_solucao,
    gerar_alternativa
)
from yui_ai.core.macro_engine import existe_macro, executar_macro
from yui_ai.core.teaching_engine import iniciar_ensino


# =============================================================
# NORMALIZAÇÃO DE RETORNO (AÇÕES → ENGINE)
# =============================================================
def _normalizar_resultado(resultado):
    """
    Converte qualquer padrão de retorno em:
    { status, message, data }
    """
    if not isinstance(resultado, dict):
        return {
            "status": "error",
            "message": "Retorno inválido da ação",
            "data": {"codigo": "RETORNO_INVALIDO"}
        }

    # padrão novo
    if "status" in resultado:
        return resultado

    # padrão antigo (actions.py)
    if "ok" in resultado:
        return {
            "status": "ok" if resultado["ok"] else "error",
            "message": resultado.get("mensagem", ""),
            "data": {
                "codigo": resultado.get("codigo", "DESCONHECIDO"),
                **resultado.get("dados", {})
            }
        }

    return {
        "status": "error",
        "message": "Formato de retorno desconhecido",
        "data": {"codigo": "FORMATO_INVALIDO"}
    }


# =============================================================
# EXECUÇÃO COM CONTROLE, APRENDIZADO E AUTOCORREÇÃO
# =============================================================
def executar_com_controle(acao, dados, executar_acao_func, falar):
    # =============================
    # 0️⃣ EXECUÇÃO DIRETA (MACROS FUTURAS)
    # =============================
    if existe_macro(acao):
        bruto = executar_macro(
            acao,
            executar_acao_func,
            falar
        )
    else:
        bruto = executar_acao_func(acao, dados)

    resultado = _normalizar_resultado(bruto)

    # =============================
    # SUCESSO
    # =============================
    if resultado["status"] == "ok":
        salvar_solucao(acao, dados)
        falar(resultado.get("message", "Executado com sucesso."))
        return resultado

    # =============================
    # FALHA
    # =============================
    mensagem = resultado.get("message", "")
    codigo = resultado.get("data", {}).get("codigo", "ERRO_DESCONHECIDO")

    registrar_falha_acao(acao, f"{codigo} | {mensagem}")

    # 1️⃣ tenta solução aprendida
    solucao = buscar_solucao(acao, dados)
    if solucao and solucao != dados:
        falar("Vou tentar do jeito que funcionou antes.")
        return executar_com_controle(
            acao,
            solucao,
            executar_acao_func,
            falar
        )

    # 2️⃣ tenta alternativa automática
    alternativa = gerar_alternativa(acao, dados)
    if alternativa:
        falar("Tentando uma alternativa.")
        return executar_com_controle(
            alternativa["acao"],
            alternativa["dados"],
            executar_acao_func,
            falar
        )

    # 3️⃣ falha final → ensino
    falar(
        "Não consegui fazer sozinha. "
        "Se você quiser, posso aprender observando."
    )
    iniciar_ensino(acao)

    return {
        "status": "error",
        "message": "Falha após todas as tentativas",
        "data": {
            "codigo": "FALHA_FINAL",
            "acao": acao
        }
    }


# =============================================================
# EXECUÇÃO DE PLANOS (ESTRUTURA PRONTA, SEM CONFLITO)
# =============================================================
PLANO_ATUAL = None
ETAPA_ATUAL = 0


def iniciar_plano(plano=None):
    global PLANO_ATUAL, ETAPA_ATUAL
    PLANO_ATUAL = plano
    ETAPA_ATUAL = 0

    return {
        "status": "ok",
        "message": "Plano iniciado",
        "data": plano
    }


def proxima_etapa():
    global ETAPA_ATUAL, PLANO_ATUAL

    if not PLANO_ATUAL:
        return {
            "status": "error",
            "message": "Nenhum plano ativo",
            "data": None
        }

    if ETAPA_ATUAL >= len(PLANO_ATUAL.get("etapas", [])):
        return {
            "status": "ok",
            "message": "Plano finalizado",
            "data": None
        }

    etapa = PLANO_ATUAL["etapas"][ETAPA_ATUAL]
    ETAPA_ATUAL += 1

    return {
        "status": "ok",
        "message": "Próxima etapa obtida",
        "data": etapa
    }


def concluir_etapa():
    return {
        "status": "ok",
        "message": "Etapa concluída",
        "data": None
    }
