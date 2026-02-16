# sequence_engine.py

import time

# =============================
# CONFIGURAÇÃO PADRÃO
# =============================
TEMPO_PADRAO_ESPERA = 2.5  # segundos


def dividir_comandos(texto):
    """
    Divide comandos por conectores naturais
    """
    conectores = [
        ", depois",
        ", em seguida",
        ", e depois",
        " depois ",
        " e depois ",
        " em seguida ",
        ",",
        " e "
    ]

    comandos = [texto]

    for c in conectores:
        novos = []
        for bloco in comandos:
            novos.extend(bloco.split(c))
        comandos = novos

    return [c.strip() for c in comandos if c.strip()]


def executar_sequencia(
    comandos,
    interpretar_intencao,
    decidir_proxima_acao,
    executar_com_controle,
    executar_acao,
    falar,
    memoria
):
    falar(f"Executando {len(comandos)} comandos em sequência.")

    for i, texto in enumerate(comandos, start=1):
        falar(f"Passo {i}: {texto}")

        intencao = interpretar_intencao(texto)
        if intencao.get("tipo") == "conversa":
            falar("Esse passo parece conversa. Pulando.")
            continue

        decisao = decidir_proxima_acao(intencao, True, memoria)

        if not decisao or decisao.get("status") != "ok":
            falar("Não consegui autorizar esse passo. Pulando.")
            continue

        dados_decisao = decisao.get("data", {}) or {}
        acao = dados_decisao.get("acao")
        dados = dados_decisao.get("dados", {}) or {}

        if not acao:
            falar("Esse passo não tem uma ação clara. Pulando.")
            continue

        resultado = executar_com_controle(
            acao,
            dados,
            executar_acao,
            falar
        )

        # ⏳ espera após cada comando
        if not isinstance(resultado, dict) or resultado.get("status") != "ok":
            falar("Sequência interrompida por falha.")
            return False

        tempo = tempo_espera_para_acao(acao)
        time.sleep(tempo)

    falar("Sequência concluída.")
    return True


def tempo_espera_para_acao(acao):
    """
    Esperas inteligentes por tipo de ação
    """
    if acao in ["abrir_app", "abrir_qualquer_coisa"]:
        return 4.0

    if acao in ["abrir_site", "navegar_site"]:
        return 5.0

    return TEMPO_PADRAO_ESPERA
