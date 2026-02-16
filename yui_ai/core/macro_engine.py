# macro_engine.py

from yui_ai.memory.memory import (
    obter_memoria,
    salvar_memoria
)

# =============================
# MACROS
# =============================

def salvar_macro(nome, passos):
    memoria = obter_memoria()

    if "macros" not in memoria:
        memoria["macros"] = {}

    memoria["macros"][nome] = passos
    salvar_memoria(memoria)

    return {
        "status": "ok",
        "message": f"Macro '{nome}' salva com sucesso",
        "data": {
            "passos": len(passos)
        }
    }


def obter_macro(nome):
    memoria = obter_memoria()
    return memoria.get("macros", {}).get(nome)


def existe_macro(nome):
    memoria = obter_memoria()
    return nome in memoria.get("macros", {})


def executar_macro(nome, executar_acao_func, falar):
    macro = obter_macro(nome)

    if not macro:
        return {
            "status": "error",
            "message": "Macro não encontrada",
            "data": {
                "codigo": "MACRO_INEXISTENTE",
                "macro": nome
            }
        }

    falar("Executando do jeito que você me ensinou.")

    for indice, passo in enumerate(macro):
        resultado = executar_acao_func(
            passo["acao"],
            passo.get("dados", {})
        )

        # 🔒 Garante padrão
        if not isinstance(resultado, dict) or "status" not in resultado:
            return {
                "status": "error",
                "message": "Retorno inválido durante execução da macro",
                "data": {
                    "codigo": "RETORNO_INVALIDO",
                    "macro": nome,
                    "etapa": indice
                }
            }

        # ❌ Falha em algum passo
        if resultado["status"] != "ok":
            return {
                "status": "error",
                "message": f"Falha na etapa {indice + 1} da macro",
                "data": {
                    "codigo": "FALHA_MACRO",
                    "macro": nome,
                    "etapa": indice,
                    "resultado": resultado
                }
            }

    return {
        "status": "ok",
        "message": f"Macro '{nome}' executada com sucesso",
        "data": {
            "macro": nome,
            "etapas": len(macro)
        }
    }
