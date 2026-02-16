from yui_ai.memory.memory import obter_autonomia, obter_erros_acao

ACOES_SIMPLES = [
    "abrir",
    "executar",
    "mostrar",
    "exibir",
    "listar",
    "explicar",
    "resumo",
    "roadmap",
    "status"
]

ACOES_SENSIVEIS = [
    "apagar",
    "deletar",
    "excluir",
    "refatorar",
    "alterar",
    "modificar"
]

MAX_FALHAS_PERMITIDAS = 2

def pode_executar_sozinha(descricao_acao: str) -> bool:
    if not descricao_acao:
        return False

    descricao = descricao_acao.lower()
    autonomia = obter_autonomia()
    nivel = autonomia.get("nivel", 1)

    # 🔴 ações perigosas nunca são automáticas
    if any(p in descricao for p in ACOES_SENSIVEIS):
        return False

    # 🔥 memória de erro bloqueia autonomia
    erros = obter_erros_acao(descricao)
    if erros.get("falhas", 0) >= MAX_FALHAS_PERMITIDAS:
        return False

    # 🟡 nível 1
    if nivel == 1:
        return False

    # 🟢 nível 2
    if nivel == 2:
        return any(p in descricao for p in ACOES_SIMPLES)

    # 🚀 nível 3
    if nivel >= 3:
        return True

    return False
