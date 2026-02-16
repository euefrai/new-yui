from yui_ai.memory.memory import acao_esta_bloqueada


def decidir_proxima_acao(intencao, permitido, memoria=None, contexto=None):
    """
    Decide se uma ação pode ser executada com base em:
    - intenção interpretada
    - permissões globais
    - bloqueios por falha (D14)
    - contexto atual
    """

    # =============================
    # VALIDAÇÃO BÁSICA
    # =============================
    if not isinstance(intencao, dict):
        return {
            "status": "error",
            "message": "Intenção inválida",
            "data": {}
        }

    acao = intencao.get("acao")
    dados = intencao.get("dados", {})

    # =============================
    # SEM AÇÃO → SEGUIR CONVERSA
    # =============================
    if not acao or acao == "nenhuma":
        return {
            "status": "ok",
            "message": "Nenhuma ação necessária",
            "data": {}
        }

    # =============================
    # PERMISSÃO GLOBAL
    # =============================
    if not permitido:
        return {
            "status": "error",
            "message": "Ação não permitida pelo sistema",
            "data": {
                "acao": acao,
                "motivo": "PERMISSAO_GLOBAL"
            }
        }

    # =============================
    # BLOQUEIO POR FALHAS (D14)
    # =============================
    bloqueio = acao_esta_bloqueada(acao)
    if bloqueio.get("data", {}).get("bloqueado"):
        return {
            "status": "error",
            "message": "Ação bloqueada por falhas repetidas",
            "data": {
                "acao": acao,
                "motivo": "BLOQUEIO_D14",
                "tentativas": bloqueio["data"].get("tentativas", 0)
            }
        }

    # =============================
    # CONTEXTO → CONFIRMAÇÃO
    # =============================
    if contexto:
        if contexto.get("modo") == "acao_pendente" and not contexto.get("confirmado"):
            return {
                "status": "ok",
                "message": "Aguardando confirmação do usuário",
                "data": {
                    "acao": acao,
                    "dados": dados,
                    "requer_confirmacao": True
                }
            }

    # =============================
    # EXECUÇÃO AUTORIZADA
    # =============================
    return {
        "status": "ok",
        "message": "Ação autorizada para execução",
        "data": {
            "acao": acao,
            "dados": dados
        }
    }
