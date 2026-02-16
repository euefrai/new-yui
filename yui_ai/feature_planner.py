from yui_ai.memory.memory import obter_memoria, registrar_plano

def gerar_plano_feature(item):
    plano = {
        "titulo": item["titulo"],
        "objetivo": f"Implementar {item['titulo'].lower()}",
        "etapas": [
            "Analisar impacto no projeto",
            "Definir mudanças necessárias",
            "Aplicar alterações com segurança",
            "Validar comportamento",
            "Atualizar documentação viva"
        ],
        "status": "proposto"
    }

    registrar_plano(plano)
    return plano
