"""
Engine de geração e aplicação de diffs unificados.

Usa difflib para gerar diffs contextuais seguros.
"""

import difflib
from typing import List, Tuple, Optional


def gerar_diff(conteudo_antigo: str, conteudo_novo: str, arquivo: str = "") -> List[dict]:
    """
    Gera um diff unificado entre dois conteúdos.

    Retorna lista de hunks (blocos de mudança):
    [
        {
            "tipo": "igual" | "adicionar" | "remover" | "modificar",
            "linha_inicio": int,
            "linhas_antigas": List[str],
            "linhas_novas": List[str],
            "contexto": List[str]  # linhas ao redor para contexto
        },
        ...
    ]
    """
    linhas_antigas = conteudo_antigo.splitlines(keepends=True)
    linhas_novas = conteudo_novo.splitlines(keepends=True)

    diff = difflib.unified_diff(
        linhas_antigas,
        linhas_novas,
        fromfile=arquivo or "original",
        tofile=arquivo or "modificado",
        lineterm="",
        n=3  # contexto de 3 linhas
    )

    hunks = []
    hunk_atual = None
    linha_atual = 0

    for linha in diff:
        if linha.startswith("@@"):
            # Novo hunk
            if hunk_atual:
                hunks.append(hunk_atual)

            # Parse @@ -start,count +start,count @@
            partes = linha.split()
            if len(partes) >= 3:
                antigo_info = partes[1]  # -start,count
                novo_info = partes[2]  # +start,count

                linha_inicio_antiga = int(antigo_info.split(",")[0].replace("-", ""))
                linha_inicio_nova = int(novo_info.split(",")[0].replace("+", ""))

                hunk_atual = {
                    "tipo": "modificar",
                    "linha_inicio_antiga": linha_inicio_antiga - 1,  # 0-indexed
                    "linha_inicio_nova": linha_inicio_nova - 1,
                    "linhas_antigas": [],
                    "linhas_novas": [],
                    "contexto_antes": [],
                    "contexto_depois": []
                }
        elif hunk_atual and linha.startswith(" "):
            # Linha igual (contexto)
            conteudo = linha[1:]  # remove espaço inicial
            if len(hunk_atual["linhas_antigas"]) == 0:
                hunk_atual["contexto_antes"].append(conteudo)
            else:
                hunk_atual["contexto_depois"].append(conteudo)
        elif hunk_atual and linha.startswith("-"):
            # Linha removida
            hunk_atual["linhas_antigas"].append(linha[1:])
            hunk_atual["tipo"] = "remover" if not hunk_atual["linhas_novas"] else "modificar"
        elif hunk_atual and linha.startswith("+"):
            # Linha adicionada
            hunk_atual["linhas_novas"].append(linha[1:])
            if not hunk_atual["linhas_antigas"]:
                hunk_atual["tipo"] = "adicionar"

    if hunk_atual:
        hunks.append(hunk_atual)

    return hunks


def aplicar_diff(conteudo_original: str, hunks: List[dict]) -> Tuple[str, bool]:
    """
    Aplica um diff (lista de hunks) em um conteúdo original.

    Retorna: (conteudo_modificado, sucesso)
    """
    linhas = conteudo_original.splitlines(keepends=True)
    linhas_resultado = linhas.copy()
    offset = 0  # compensação por linhas removidas/adicionadas

    for hunk in hunks:
        linha_inicio = hunk["linha_inicio_antiga"] + offset

        # Validação: verifica se o contexto bate
        contexto_antes = hunk.get("contexto_antes", [])
        if contexto_antes:
            inicio_valido = linha_inicio - len(contexto_antes)
            if inicio_valido < 0:
                return conteudo_original, False

            for i, linha_esperada in enumerate(contexto_antes):
                idx = inicio_valido + i
                if idx >= len(linhas_resultado) or linhas_resultado[idx] != linha_esperada:
                    return conteudo_original, False

        # Remove linhas antigas
        num_remover = len(hunk["linhas_antigas"])
        if num_remover > 0:
            del linhas_resultado[linha_inicio:linha_inicio + num_remover]
            offset -= num_remover

        # Adiciona linhas novas
        num_adicionar = len(hunk["linhas_novas"])
        if num_adicionar > 0:
            linhas_resultado[linha_inicio:linha_inicio] = hunk["linhas_novas"]
            offset += num_adicionar

    return "".join(linhas_resultado), True


def visualizar_diff(hunks: List[dict], arquivo: str = "") -> str:
    """
    Gera uma visualização legível do diff.
    """
    if not hunks:
        return f"Nenhuma mudança em {arquivo}"

    linhas = [f"📝 Mudanças em {arquivo}:"]
    linhas.append("")

    for i, hunk in enumerate(hunks, 1):
        tipo = hunk["tipo"]
        linha_inicio = hunk["linha_inicio_antiga"] + 1  # 1-indexed para exibição

        linhas.append(f"  Hunk {i} (linha {linha_inicio}): {tipo}")

        if hunk["linhas_antigas"]:
            linhas.append("    Removido:")
            for linha in hunk["linhas_antigas"]:
                linhas.append(f"      - {linha.rstrip()}")

        if hunk["linhas_novas"]:
            linhas.append("    Adicionado:")
            for linha in hunk["linhas_novas"]:
                linhas.append(f"      + {linha.rstrip()}")

        linhas.append("")

    return "\n".join(linhas)
