def analisar_problemas(projeto):
    problemas = []

    for arquivo, info in projeto.items():
        tipo = info.get("tipo")
        imports = info.get("imports", [])
        funcoes = info.get("funcoes", [])

        # 1️⃣ core sobrecarregado
        if tipo == "core" and len(imports) > 8:
            problemas.append(
                f"{arquivo} é um CORE com muitos imports ({len(imports)}). "
                "Considere dividir responsabilidades."
            )

        # 2️⃣ arquivo fazendo coisa demais
        if len(funcoes) > 12:
            problemas.append(
                f"{arquivo} possui muitas funções ({len(funcoes)}). "
                "Pode estar fazendo mais de uma coisa."
            )

        # 3️⃣ interface acessando infra demais
        if tipo == "interface":
            if any("memory" in imp or "storage" in imp for imp in imports):
                problemas.append(
                    f"{arquivo} (interface) acessa diretamente a camada de memória."
                )

        # 4️⃣ utilitário com dependência excessiva
        if tipo == "util" and len(imports) > 5:
            problemas.append(
                f"{arquivo} (util) tem dependências demais ({len(imports)})."
            )

    return problemas
