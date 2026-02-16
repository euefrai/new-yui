from graphviz import Digraph
import os

def gerar_mapa_visual(projeto, saida="mapa_vexx"):
    dot = Digraph(comment="Arquitetura do Projeto VEXX", format="png")

    cores = {
        "core": "red",
        "infra": "blue",
        "interface": "green",
        "util": "gray"
    }

    for arquivo, info in projeto.items():
        nome = os.path.basename(arquivo)
        tipo = info.get("tipo", "util")
        cor = cores.get(tipo, "gray")

        label = f"{nome}\n[{tipo}]\n{info.get('responsabilidade','')}"
        dot.node(nome, label=label, style="filled", fillcolor=cor)

    # dependências (imports)
    for arquivo, info in projeto.items():
        origem = os.path.basename(arquivo)
        for imp in info.get("imports", []):
            destino = imp.split(".")[0] + ".py"
            dot.edge(origem, destino)

    dot.render(saida, cleanup=True)
    return f"{saida}.png"
