from yui_ai.memory.memory import registrar_rollback, atualizar_documentacao_viva

def refatoracoes_seguras():
    """ Retorna a lista de melhorias que a Yui pode aplicar sem supervisão humana. """
    return [
        {
            "id": "separar_responsabilidades",
            "descricao": "Separei responsabilidades para reduzir acoplamento."
        },
        {
            "id": "organizar_fluxo",
            "descricao": "Organizei o fluxo principal para ficar mais claro."
        },
        {
            "id": "limpeza_estrutura",
            "descricao": "Removi redundâncias estruturais sem alterar comportamento."
        }
    ]

def aplicar_refatoracao_segura(refatoracao):
    """ 
    Executa a lógica de refatoração, registra no rollback e 
    atualiza a documentação viva do projeto. 
    """
    
    # 1. Registra o estado anterior para permitir o comando 'rollback'
    registrar_rollback(refatoracao["descricao"])

    # 2. Atualiza a Documentação Viva com a nova decisão arquitetural
    atualizar_documentacao_viva(
        decisao=f"Melhoria automática: {refatoracao['descricao']}"
    )

    # 3. Aqui, no futuro, você pode inserir chamadas para o refactor_engine
    # para alterar arquivos físicos usando AST ou Regex.

    # 4. Retorna o resultado para o loop principal (main.py)
    return {
        "id": refatoracao["id"],
        "descricao": refatoracao["descricao"],
        "status": "sucesso"
    }