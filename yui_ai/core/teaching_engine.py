# teaching_engine.py

from yui_ai.core.macro_engine import salvar_macro

MODO_ENSINO = {
    "ativo": False,
    "acao": None,
    "passos": []
}

def iniciar_ensino(acao):
    MODO_ENSINO["ativo"] = True
    MODO_ENSINO["acao"] = acao
    MODO_ENSINO["passos"] = []


def registrar_passo(acao, dados):
    if not MODO_ENSINO["ativo"]:
        return
    MODO_ENSINO["passos"].append({
        "acao": acao,
        "dados": dados
    })


def finalizar_ensino():
    if not MODO_ENSINO["ativo"]:
        return False

    salvar_macro(
        MODO_ENSINO["acao"],
        MODO_ENSINO["passos"]
    )

    MODO_ENSINO["ativo"] = False
    return True
    