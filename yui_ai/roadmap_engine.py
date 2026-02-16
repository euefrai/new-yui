from yui_ai.memory.memory import obter_memoria, atualizar_roadmap

def gerar_roadmap():
    memoria = obter_memoria()
    projeto = memoria["projetos"]["vexx"]

    roadmap = []

    if not projeto.get("documentacao_viva", {}).get("resumo"):
        roadmap.append("Consolidar documentação viva do projeto.")

    if len(projeto.get("aprendizados", [])) < 3:
        roadmap.append("Aprofundar aprendizados técnicos do projeto.")

    if projeto.get("auto_confiança", 1) < 3:
        roadmap.append("Aumentar confiança do modo automático.")

    if not projeto.get("rollback_stack"):
        roadmap.append("Testar e validar o mecanismo de rollback.")

    if not roadmap:
        roadmap.append("Projeto está maduro. Focar em novas funcionalidades.")

    for item in roadmap:
        atualizar_roadmap(item)

    return roadmap
