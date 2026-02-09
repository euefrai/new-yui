def sugerir_refatoracoes(problemas):
    sugestoes = []

    for p in problemas:
        texto = p.lower()

        if "core com muitos imports" in texto or "muitas responsabilidades" in texto:
            sugestoes.append({
                "problema": p,
                "sugestao": "Extrair responsabilidades do core",
                "acao": (
                    "Criar módulos específicos (ex: mode_controller.py, "
                    "memory_manager.py) e mover lógica para eles."
                )
            })

        if "muitas funções" in texto:
            sugestoes.append({
                "problema": p,
                "sugestao": "Separar responsabilidades",
                "acao": (
                    "Dividir o arquivo em módulos menores por responsabilidade."
                )
            })

        if "interface" in texto and "memória" in texto:
            sugestoes.append({
                "problema": p,
                "sugestao": "Criar camada intermediária",
                "acao": (
                    "Adicionar um service layer entre interface e memória."
                )
            })

    return sugestoes


def gerar_refatoracao(problema):
    problema = problema.lower()

    if "main.py" in problema and "acoplamento" in problema:
        return {
            "id": "extrair_mode_controller",
            "titulo": "Separar controle de modos",
            "descricao": "Extrair a lógica de texto/voz para um módulo dedicado.",
            "impacto": "Reduz acoplamento e facilita adicionar novos modos.",
            "arquivos": ["main.py", "mode_controller.py"]
        }

    return None

def ciclo_d5_concluido():
    return True
