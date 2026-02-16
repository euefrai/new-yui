from yui_ai.memory.memory import atualizar_roadmap_item, obter_memoria

def calcular_prioridade(impacto, esforco, risco):
    return impacto - esforco - risco


def priorizar_roadmap():
    memoria = obter_memoria()
    projeto = memoria["projetos"]["vexx"]

    itens = []

    # exemplos de heurísticas reais
    if projeto.get("auto_confiança", 1) < 3:
        itens.append({
            "titulo": "Fortalecer modo automático",
            "impacto": 5,
            "esforco": 2,
            "risco": 1
        })

    if not projeto.get("rollback_stack"):
        itens.append({
            "titulo": "Validar rollback em cenários reais",
            "impacto": 4,
            "esforco": 2,
            "risco": 1
        })

    if not projeto.get("documentacao_viva", {}).get("arquitetura"):
        itens.append({
            "titulo": "Consolidar arquitetura na documentação viva",
            "impacto": 4,
            "esforco": 1,
            "risco": 0
        })

    if not itens:
        itens.append({
            "titulo": "Explorar novas funcionalidades",
            "impacto": 3,
            "esforco": 2,
            "risco": 1
        })

    # calcula prioridade
    for item in itens:
        item["prioridade"] = calcular_prioridade(
            item["impacto"],
            item["esforco"],
            item["risco"]
        )
        atualizar_roadmap_item(item)

    # retorna ordenado
    return sorted(itens, key=lambda x: x["prioridade"], reverse=True)
