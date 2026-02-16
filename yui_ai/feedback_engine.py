from yui_ai.memory.memory import obter_feedbacks

def analisar_feedbacks():
    feedbacks = obter_feedbacks()

    if not feedbacks:
        return "Ainda não tenho feedback suficiente para ajustar o planejamento."

    sucesso = sum(1 for f in feedbacks if f["resultado"] == "sucesso")
    falha = sum(1 for f in feedbacks if f["resultado"] == "falha")

    if falha > sucesso:
        return (
            "Notei mais falhas que sucessos. "
            "Vou reduzir riscos e propor mudanças menores."
        )

    return (
        "Os resultados estão positivos. "
        "Posso avançar com planos mais ambiciosos."
    )
