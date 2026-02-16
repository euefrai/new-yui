import os
import sys
import threading
import queue

# =============================================================
# CONSOLE UTF-8 (EVITA UnicodeEncodeError NO WINDOWS)
# =============================================================
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    # Alguns ambientes/hosts não suportam reconfigure
    pass

# =============================================================
# BOOTSTRAP DE PATH (PERMITE RODAR COMO SCRIPT OU MÓDULO)
# =============================================================
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# =============================
# IMPORTS DE SISTEMA
# =============================
from yui_ai.core.intent_parser import interpretar_intencao
from yui_ai.core.decision_engine import decidir_proxima_acao
from yui_ai.core.ai_engine import perguntar_yui
from yui_ai.actions.actions import executar_acao
from yui_ai.permissions.permissions import permitido
from yui_ai.voice.voice import ouvir, falar
from yui_ai.core.autonomy_engine import pode_executar_sozinha

from yui_ai.core.execution_engine import executar_com_controle
from yui_ai.core.sequence_engine import dividir_comandos, executar_sequencia
from yui_ai.core.teaching_engine import finalizar_ensino

from yui_ai.memory.memory import (
    obter_memoria,
    registrar_conversa,
    atualizar_perfil,
    aumentar_autonomia,
    set_contexto,
    get_contexto,
    iniciar_execucao_acao,
    concluir_execucao,
    acao_esta_bloqueada,
    limpar_falha_acao,
    obter_documentacao_viva
)

from yui_ai.logging_setup import get_logger
from yui_ai.memory import chat_memory
from yui_ai.ai.code_generator import gerar_codigo, eh_pedido_de_codigo

# =============================
# CONFIGURAÇÕES GERAIS
# =============================
MODO_TEXTO = "texto"
MODO_VOZ = "voz"

# =============================
# EDIÇÃO CONTEXTUAL DE RESPOSTA
# =============================
def editar_resposta_anterior(pedido: str, memoria=None):
    """
    Usa a última mensagem da Yui como base e aplica o pedido do usuário.
    Retorna (resposta_texto, None). Se não houver mensagem anterior, retorna mensagem de erro.
    NUNCA inventa conteúdo.
    """
    if memoria is None:
        memoria = chat_memory
    ultima = memoria.get_last_from_yui()
    if not ultima or not (ultima.get("conteudo") or "").strip():
        return "Não encontrei uma resposta anterior para editar. Me diga qual parte você quer alterar.", None
    contexto_original = (ultima.get("conteudo") or "")[:4000]
    prompt = (
        "O usuário pediu para editar sua resposta anterior. "
        "Resposta anterior (use como base, não invente o que não está aqui):\n\n"
        f"{contexto_original}\n\n"
        f"Pedido do usuário: {pedido}\n\n"
        "Gere a versão alterada. Use exatamente este formato:\n"
        "🛠️ O QUE FOI ALTERADO\n- item 1\n- item 2\n\n"
        "📄 NOVA VERSÃO\n(conteúdo atualizado)\n\n"
        "Seja direta e técnica. Não invente conteúdo que não estava na resposta anterior."
    )
    resposta = perguntar_yui(prompt, {"tipo": "conversa"})
    texto = ""
    if isinstance(resposta, dict) and resposta.get("status") == "ok":
        data = resposta.get("data", "")
        if isinstance(data, dict):
            texto = data.get("resposta", "") or ""
        else:
            texto = str(data)
    elif isinstance(resposta, str):
        texto = resposta
    if not texto:
        texto = "Tive um problema ao gerar a edição. Tente de novo."
    return texto, None


# =============================
# FUNÇÃO DE RESPOSTA DA IA
# =============================
def responder_com_ia(texto, intencao=None, falar_fn=None):
    falar_use = falar_fn or falar
    resposta = perguntar_yui(texto, intencao)
    if not resposta:
        falar_use("Não entendi direito. Pode repetir?")
        return

    if isinstance(resposta, dict):
        if resposta.get("status") == "ok":
            data = resposta.get("data", "")
            if isinstance(data, dict):
                falar_use(data.get("resposta", "") or "")
            else:
                falar_use(str(data))
        else:
            falar_use("Tive um problema ao pensar. Pode repetir?")
    elif isinstance(resposta, str):
        falar_use(resposta)


def processar_texto_web(texto: str, reply_to_id: str = None):
    """
    Processa mensagem para a interface web. Suporta conversa, reply e edição de resposta.
    Retorna (resposta: str, message_id: Optional[str], api_key_missing: bool).
    """
    texto = (texto or "").strip()
    if not texto:
        return "Mensagem vazia.", None, False

    memoria = chat_memory
    intencao = interpretar_intencao(texto)

    # Edição de resposta anterior: usa memória, não pede reenvio
    if intencao.get("tipo") == "editar_resposta":
        pedido = intencao.get("dados", {}).get("pedido", texto)
        resposta_txt, _ = editar_resposta_anterior(pedido, memoria)
        msg_yui = memoria.add_message("yui", resposta_txt, "texto")
        return resposta_txt, msg_yui.get("id"), False

    if intencao.get("tipo") != "conversa":
        return "A interface web suporta apenas conversa e edição de resposta (ex.: 'altera isso', 'melhora o código').", None, False

    # Guarda mensagem do usuário
    memoria.add_message("usuario", texto, "texto")

    # Contexto de reply: anexa mensagem referenciada
    texto_para_ia = texto
    if reply_to_id:
        ref = memoria.get_message_by_id(reply_to_id)
        if ref and ref.get("conteudo"):
            trecho = (ref.get("conteudo") or "")[:2000]
            texto_para_ia = f"[Respondendo à mensagem anterior]:\n{trecho}\n\n[Pergunta/Comentário do usuário]: {texto}"

    api_key_missing = False

    # Pedido de geração de código: rota direta para gerar_codigo (📦 🧠 💻 ⚙️)
    if eh_pedido_de_codigo(texto):
        ok_codigo, resposta_txt, err_codigo = gerar_codigo(texto)
        if not ok_codigo:
            resposta_txt = err_codigo or "Não consegui gerar o código. Tente de novo."
            if err_codigo and "OPENAI_API_KEY" in err_codigo:
                api_key_missing = True
    else:
        resposta = perguntar_yui(texto_para_ia, intencao)
        resposta_txt = ""
        if not resposta:
            resposta_txt = "Não entendi direito. Pode repetir?"
        elif isinstance(resposta, dict):
            api_key_missing = bool(resposta.get("api_key_missing"))
            if resposta.get("status") == "ok" or api_key_missing:
                data = resposta.get("data", "")
                if isinstance(data, dict):
                    resposta_txt = data.get("resposta", "") or ""
                else:
                    resposta_txt = str(data)
            else:
                resposta_txt = "Tive um problema ao pensar. Pode repetir?"
        elif isinstance(resposta, str):
            resposta_txt = resposta
        else:
            resposta_txt = "Não consegui gerar uma resposta válida."

    msg_yui = memoria.add_message("yui", resposta_txt, "texto")
    return resposta_txt, msg_yui.get("id"), api_key_missing

# =============================
# LOOP PRINCIPAL (ENTRYPOINT)
# =============================
def run(input_func=None, output_func=None):
    """
    input_func: se fornecido, usa em vez de input() (ex.: GUI).
    output_func(author, text): se fornecido, envia falar/print para a GUI.
    """
    logger = get_logger()

    modo = MODO_TEXTO
    permission_level = 3

    if output_func:
        falar_out = (lambda t: output_func("Yui", t))
        print_out = (lambda *a, **k: output_func("Yui", " ".join(str(x) for x in a)))
    else:
        # Modo console: imprimir em stderr para não ser lido por input() (evita duplicar e ler resposta como se fosse do usuário)
        def falar_out(t):
            if t:
                print("Yui:", t, file=sys.stderr)
            try:
                falar(t)
            except Exception:
                pass
        def print_out_console(*args, **kwargs):
            print(*args, file=sys.stderr, **kwargs)
        print_out = print_out_console

    logger.info("Sistema Yui iniciado (modo=%s)", "GUI" if input_func and output_func else "console")
    print_out("🔥 SISTEMA YUI / VEXX INICIADO 🔥")

    # Fase 2: Wake word SOMENTE por áudio — fila para teclado e wake (quando não é GUI)
    entrada_queue = None
    wake_words_audio = ["yui", "iui"]

    def _thread_teclado(q):
        while True:
            try:
                x = input("Você: ").strip()
                if x:
                    q.put(("input", x))
            except (EOFError, KeyboardInterrupt):
                q.put(("input", "sair"))
                break

    def _thread_wake_audio(q):
        while True:
            try:
                t = ouvir(timeout=2, limite=3)
                if t and any(w in (t or "").lower() for w in wake_words_audio):
                    q.put(("wake", None))
            except Exception:
                pass

    if input_func is None:
        entrada_queue = queue.Queue()
        threading.Thread(target=_thread_teclado, args=(entrada_queue,), daemon=True).start()
        try:
            threading.Thread(target=_thread_wake_audio, args=(entrada_queue,), daemon=True).start()
        except Exception:
            pass

    while True:
        memoria = obter_memoria()
        ctx = get_contexto()

        if input_func:
            user_input = (input_func() or "").strip()
            if not user_input:
                continue
        elif entrada_queue is not None:
            kind, val = entrada_queue.get()
            if kind == "wake":
                print_out("✨ Yui acordou! Escutando...")
                falar_out("Sim, estou ouvindo")
                user_input = (ouvir(timeout=8, limite=10) or "").strip()
                if not user_input:
                    falar_out("Não ouvi nada. Voltando ao modo texto.")
                    continue
                print_out(f"Você disse: {user_input}")
            else:
                user_input = (val or "").strip()
                if not user_input:
                    continue
        else:
            user_input = input("Você: ").strip()
            if not user_input:
                continue

        texto = user_input.lower()
        logger.info("Entrada usuário: %s", user_input)
        registrar_conversa(user_input)
        atualizar_perfil()

        # =============================
        # COMANDOS DE SISTEMA / MODOS
        # =============================
        if texto in ["sair", "exit", "quit"]:
            falar_out("Desligando sistemas. Até logo 💙")
            logger.info("Comando de saída recebido. Encerrando loop principal.")
            break

        if texto in ["texto", "modo texto"]:
            modo = MODO_TEXTO
            falar_out("Voltando para o teclado.")
            logger.info("Modo alterado para TEXTO.")
            continue

        # =============================
        # CONFIRMAÇÃO DE AÇÃO PENDENTE
        # =============================
        confirmacoes = ["sim", "ok", "pode", "manda ver", "confirmado", "executar"]
        if texto in confirmacoes:
            # ---------- Fase 5: Confirmação do PLANO de edição (antes de gerar código)
            if ctx.get("modo") == "plano_edicao_pendente" and ctx.get("dados_acao"):
                dados_plano = ctx["dados_acao"]
                acao_pos_plano = dados_plano.get("acao")
                dados_pos_plano = dados_plano.get("dados", {})

                falar_out("Gerando código via IA...")
                iniciar_execucao_acao(acao_pos_plano)
                resultado = executar_acao(acao_pos_plano, dados_pos_plano)
                concluir_execucao()

                if resultado.get("ok"):
                    dados_resultado = resultado.get("dados", {})
                    patch = dados_resultado.get("patch")
                    visualizacao = dados_resultado.get("visualizacao", "")
                    explicacao = dados_resultado.get("explicacao", "")
                    arquivo = dados_resultado.get("arquivo", "")

                    print_out("\n" + "="*60)
                    print_out(explicacao)
                    print_out("="*60 + "\n")
                    print_out(visualizacao)
                    falar_out(f"Código gerado para {os.path.basename(arquivo)}. Posso aplicar essas mudanças?")

                    set_contexto(
                        modo="edicao_codigo_pendente",
                        dados_acao={
                            "acao": "aplicar_edicao_codigo",
                            "patch": patch,
                            "arquivo": arquivo
                        }
                    )
                else:
                    msg_erro = resultado.get("mensagem", "Erro ao gerar código via IA")
                    logger.error("Erro ao gerar código via IA: %s", msg_erro)
                    falar_out(msg_erro)
                    set_contexto(modo=None, dados_acao=None)

                continue

            if ctx.get("modo") == "acao_pendente" and ctx.get("dados_acao"):
                dados_pendentes = ctx["dados_acao"]
                acao_p = dados_pendentes.get("acao")
                params_p = dados_pendentes.get("dados", {})

                iniciar_execucao_acao(acao_p)
                logger.info("Confirmando acao pendente: %s", acao_p)
                resultado = executar_com_controle(acao_p, params_p, executar_acao, falar_out)
                concluir_execucao()

                if resultado.get("status") == "ok":
                    limpar_falha_acao(acao_p)
                    aumentar_autonomia()
                    logger.info("Acao pendente concluida com sucesso: %s", acao_p)
                else:
                    logger.error("Falha ao executar acao pendente %s: %s", acao_p, resultado)

                set_contexto(modo=None, dados_acao=None)  # limpa o estado
                continue

            # ---------- Confirmação para APLICAR edição de código (patch já preparado)
            if ctx.get("modo") == "edicao_codigo_pendente" and ctx.get("dados_acao"):
                dados_edicao = ctx["dados_acao"]
                patch = dados_edicao.get("patch")
                arquivo = dados_edicao.get("arquivo", "")
                if patch and arquivo:
                    falar_out("Aplicando edição...")
                    iniciar_execucao_acao("aplicar_edicao_codigo")
                    resultado = executar_com_controle(
                        "aplicar_edicao_codigo",
                        {"patch": patch, "validar": True},
                        executar_acao,
                        falar_out,
                    )
                    concluir_execucao()
                    if resultado.get("status") == "ok":
                        limpar_falha_acao("aplicar_edicao_codigo")
                        falar_out("Edição aplicada com sucesso.")
                        # Validação pós-edição (resumida)
                        from yui_ai.validation.validation_engine import ValidationEngine
                        v = ValidationEngine()
                        res = v.validar_apos_edicao(arquivo, None)
                        if res.get("tem_erros"):
                            print_out("\n" + v.formatar_resultado_completo(res))
                            falar_out("Validação encontrou pontos de atenção. Revise acima.")
                        else:
                            falar_out("Validação concluída sem erros.")
                    else:
                        falar_out(resultado.get("message", "Erro ao aplicar edição."))
                set_contexto(modo=None, dados_acao=None)
                continue

        # =============================
        # NEGAÇÃO / CANCELAR CONFIRMAÇÃO
        # =============================
        negacoes = ["não", "nao", "cancelar", "nope", "n"]
        if texto in negacoes and ctx.get("modo"):
            set_contexto(modo=None, dados_acao=None)
            falar_out("Ok, cancelado.")
            continue

        # =============================
        # ENSINO E DOCUMENTAÇÃO
        # =============================
        if texto in ["pronto", "acabou", "terminou"]:
            if finalizar_ensino():
                falar_out("Aprendi! Da próxima vez faço sozinha.")
            continue

        if any(x in texto for x in ["resumo", "arquitetura"]):
            doc = obter_documentacao_viva()
            falar_out(doc.get("resumo", "Ainda não tenho um resumo completo."))
            continue

        # =============================
        # EXECUÇÃO SEQUENCIAL
        # =============================
        if "," in user_input or " depois " in user_input:
            comandos = dividir_comandos(user_input)
            if len(comandos) > 1:
                executar_sequencia(
                    comandos,
                    interpretar_intencao,
                    decidir_proxima_acao,
                    executar_com_controle,
                    executar_acao,
                    falar,
                    memoria
                )
                continue

        # =============================
        # PROCESSAMENTO DE INTENÇÃO
        # =============================
        intencao = interpretar_intencao(user_input)

        if intencao.get("tipo") == "conversa":
            responder_com_ia(user_input, intencao, falar_out)
            continue

        # Nunca falhar silenciosamente: pedir esclarecimento se intenção ambígua
        if intencao.get("tipo") == "esclarecer":
            falar_out(intencao.get("dados", {}).get("mensagem", "Não entendi. Pode repetir ou ser mais específico?"))
            continue

        # =============================
        # DECISÃO E EXECUÇÃO DIRETA
        # =============================
        decisao = decidir_proxima_acao(
            intencao,
            permitido(permission_level, intencao.get("nivel", 0)),
            memoria,
            ctx
        )

        if not decisao or decisao.get("status") != "ok":
            msg = (decisao or {}).get("message", "Não foi possível executar essa ação.")
            falar_out(msg)
            continue

        if decisao and decisao.get("status") == "ok":
            dados_decisao = decisao.get("data", {})
            acao = dados_decisao.get("acao")
            dados = dados_decisao.get("dados", {})

            if not acao:
                continue

            # =============================
            # TRATAMENTO ESPECIAL: MEMÓRIA ARQUITETURAL (CONSULTA DIRETA, REGISTRO REQUER CONFIRMAÇÃO)
            # =============================
            acoes_arquitetura = [
                "registrar_regra_arquitetural",
                "consultar_regras",
                "consultar_padroes",
                "consultar_memoria_arquitetural"
            ]

            if acao in acoes_arquitetura:
                # Consultas podem executar direto
                if acao in ["consultar_regras", "consultar_padroes", "consultar_memoria_arquitetural"]:
                    iniciar_execucao_acao(acao)
                    resultado = executar_acao(acao, dados)
                    concluir_execucao()

                    if resultado.get("ok"):
                        visualizacao = resultado.get("dados", {}).get("visualizacao")
                        if visualizacao:
                            print_out("\n" + visualizacao)
                    else:
                        falar_out(resultado.get("mensagem", "Erro ao consultar memória arquitetural"))
                    continue

                # Registrar regra requer confirmação
                if acao == "registrar_regra_arquitetural":
                    iniciar_execucao_acao(acao)
                    resultado = executar_acao(acao, dados)
                    concluir_execucao()

                    if resultado.get("ok"):
                        entrada = resultado.get("dados", {}).get("entrada", {})
                        tipo_entrada = resultado.get("dados", {}).get("tipo", "regra")
                        comando = resultado.get("dados", {}).get("comando", "")

                        # Mostra o que será registrado
                        print_out(f"\n📝 {tipo_entrada.capitalize()} a ser registrada:")
                        if tipo_entrada == "regra":
                            print_out(f"  {entrada.get('regra', comando)}")
                        elif tipo_entrada == "padrão":
                            print_out(f"  {entrada.get('nome', comando)}: {entrada.get('descricao', '')}")
                        elif tipo_entrada == "restrição":
                            print_out(f"  {entrada.get('restricao', comando)}")
                        elif tipo_entrada == "decisão":
                            print_out(f"  {entrada.get('decisao', comando)}")

                        falar_out(f"Posso salvar essa {tipo_entrada} na memória arquitetural?")

                        # Salva no contexto para confirmação
                        set_contexto(
                            modo="registro_regra_pendente",
                            dados_acao={
                                "acao": "confirmar_registro_regra",
                                "entrada": entrada,
                                "tipo": tipo_entrada
                            }
                        )
                    else:
                        falar_out(resultado.get("mensagem", "Erro ao preparar registro"))
                    continue

            # =============================
            # ANÁLISE DE PROJETO (SOMENTE LEITURA — EXECUÇÃO DIRETA, SEM CONFIRMAÇÃO)
            # =============================
            if acao == "analisar_projeto":
                iniciar_execucao_acao(acao)
                resultado = executar_acao(acao, dados)
                concluir_execucao()
                if resultado.get("ok"):
                    relatorio = resultado.get("dados", {}).get("relatorio", "")
                    if relatorio:
                        print_out(relatorio)
                    falar_out("Análise do projeto concluída. Relatório acima.")
                    limpar_falha_acao(acao)
                else:
                    falar_out(resultado.get("mensagem", "Erro ao analisar projeto."))
                continue

            # =============================
            # TRATAMENTO ESPECIAL: EDIÇÃO DE CÓDIGO (SEMPRE REQUER CONFIRMAÇÃO)
            # =============================
            acoes_edicao_codigo = [
                "preparar_edicao_codigo",
                "aplicar_edicao_codigo",
                "visualizar_edicoes_pendentes",
                "reverter_edicao_codigo",
                "obter_historico_edicoes",
                "gerar_codigo_refatorado",
                "analisar_e_corrigir_bug"
            ]

            if acao in acoes_edicao_codigo:
                # =============================
                # GERAÇÃO DE CÓDIGO VIA IA (NUNCA APLICA DIRETAMENTE)
                # =============================
                # ---------- File Resolver: validar arquivo antes de planejamento ou geração
                if acao in ["gerar_codigo_refatorado", "analisar_e_corrigir_bug"]:
                    from yui_ai.core.file_resolver import validar_arquivo_para_edicao

                    ok_arquivo, caminho_real, msg_arquivo = validar_arquivo_para_edicao(
                        dados.get("arquivo", ""),
                        raiz=PROJECT_ROOT,
                    )
                    if not ok_arquivo or not caminho_real:
                        falar_out(msg_arquivo or "Arquivo não encontrado no projeto.")
                        continue
                    dados = {**dados, "arquivo": caminho_real}

                # ---------- Fase 5: PLANO obrigatório antes de qualquer edição via IA
                if acao in ["gerar_codigo_refatorado", "analisar_e_corrigir_bug"]:
                    from yui_ai.code_editor.planning_engine import gerar_plano_edicao

                    falar_out("Gerando plano de edição...")
                    instrucao_plano = (
                        dados.get("instrucao")
                        or dados.get("descricao_bug")
                        or "Alteração/correção no código"
                    )
                    sucesso_plano, plano, erro_plano = gerar_plano_edicao(
                        dados.get("arquivo", ""),
                        instrucao_plano,
                        dados.get("contexto_adicional", ""),
                        acao,
                    )

                    if not sucesso_plano:
                        falar_out(erro_plano or "Erro ao gerar plano.")
                        continue

                    # Exibe plano de forma clara e estruturada
                    print_out(plano.get("texto_formatado", ""))

                    # Nenhuma edição sem plano aprovado: pede confirmação do plano
                    falar_out("Este é o plano de edição. Aprovar este plano para eu gerar o código?")
                    set_contexto(
                        modo="plano_edicao_pendente",
                        dados_acao={
                            "acao": acao,
                            "dados": dados,
                        }
                    )
                    continue
                # Ações de visualização/histórico podem executar direto
                if acao in ["visualizar_edicoes_pendentes", "obter_historico_edicoes"]:
                    iniciar_execucao_acao(acao)
                    resultado = executar_com_controle(acao, dados, executar_acao, falar_out)
                    concluir_execucao()

                    if resultado.get("status") == "ok":
                        # Mostra visualização se disponível
                        visualizacao = resultado.get("data", {}).get("visualizacao")
                        if visualizacao:
                            print_out("\n" + visualizacao)
                        historico = resultado.get("data", {}).get("historico")
                        if historico:
                            print_out(f"\n📚 Histórico ({len(historico)} entradas):")
                            for entrada in historico[-5:]:  # últimas 5
                                print_out(f"  - {entrada.get('descricao', 'Sem descrição')} ({entrada.get('timestamp', '')[:10]})")
                    continue

                # preparar_edicao_codigo: prepara e mostra visualização, aguarda confirmação
                if acao == "preparar_edicao_codigo":
                    iniciar_execucao_acao(acao)
                    resultado = executar_acao(acao, dados)
                    concluir_execucao()

                    if resultado.get("ok"):
                        patch = resultado.get("dados", {}).get("patch")
                        visualizacao = resultado.get("dados", {}).get("visualizacao", "")
                        arquivo = resultado.get("dados", {}).get("arquivo", "")

                        # Mostra visualização
                        print_out("\n" + visualizacao)
                        falar_out(f"Preparada edição em {os.path.basename(arquivo)}. Posso aplicar?")

                        # Salva patch no contexto para confirmação posterior
                        set_contexto(
                            modo="edicao_codigo_pendente",
                            dados_acao={
                                "acao": "aplicar_edicao_codigo",
                                "patch": patch,
                                "arquivo": arquivo
                            }
                        )
                    else:
                        falar_out(resultado.get("mensagem", "Erro ao preparar edição"))
                    continue

                # aplicar_edicao_codigo: SEMPRE requer confirmação explícita
                if acao == "aplicar_edicao_codigo":
                    # Verifica se está no contexto de confirmação
                    if ctx.get("modo") != "edicao_codigo_pendente":
                        falar_out("Não há edição pendente para aplicar. Use 'preparar edição' primeiro.")
                        continue

                    patch = dados.get("patch") or ctx.get("dados_acao", {}).get("patch")
                    if not patch:
                        falar_out("Patch não encontrado. Preparação pode ter expirado.")
                        set_contexto(modo=None, dados_acao=None)
                        continue

                    # Aplica edição
                    iniciar_execucao_acao(acao)
                    resultado = executar_com_controle(
                        acao,
                        {"patch": patch, "validar": True},
                        executar_acao,
                        falar_out
                    )
                    concluir_execucao()

                    if resultado.get("status") == "ok":
                        entrada_historico = resultado.get("data", {}).get("entrada_historico", {})
                        arquivo_modificado = patch.get("arquivo") or ctx.get("dados_acao", {}).get("arquivo", "")
                        
                        falar_out(f"Edição aplicada! ID no histórico: {entrada_historico.get('id', 'N/A')}")
                        
                        # =============================
                        # VALIDAÇÃO AUTOMÁTICA PÓS-EDIÇÃO
                        # =============================
                        falar_out("Validando código aplicado...")
                        
                        from yui_ai.validation.validation_engine import ValidationEngine
                        validator = ValidationEngine()
                        
                        # Determina diretório do projeto (tenta encontrar raiz)
                        diretorio_projeto = None
                        if arquivo_modificado:
                            raiz_candidata = os.path.dirname(arquivo_modificado)
                            # Tenta subir até encontrar indicadores de projeto
                            for _ in range(5):  # máximo 5 níveis acima
                                if any(os.path.exists(os.path.join(raiz_candidata, f)) for f in 
                                       ["pytest.ini", "setup.py", "requirements.txt", "package.json", "pyproject.toml", ".git"]):
                                    diretorio_projeto = raiz_candidata
                                    break
                                raiz_candidata = os.path.dirname(raiz_candidata)
                                if raiz_candidata == os.path.dirname(raiz_candidata):
                                    break
                        
                        resultado_validacao = validator.validar_apos_edicao(
                            arquivo_modificado,
                            diretorio_projeto
                        )
                        
                        # Mostra resultado da validação
                        print_out("\n" + validator.formatar_resultado_completo(resultado_validacao))
                        
                        # Pergunta se deve analisar erros (se houver)
                        if resultado_validacao["tem_erros"]:
                            falar_out("Encontrei alguns problemas na validação. Quer que eu analise os erros e sugira correções?")
                            # Salva resultado no contexto para possível análise posterior
                            set_contexto(
                                modo="validacao_com_erros",
                                dados_acao={
                                    "acao": "analisar_erros_validacao",
                                    "resultado_validacao": resultado_validacao,
                                    "arquivo": arquivo_modificado
                                }
                            )
                        else:
                            falar_out("Validação concluída sem erros! ✅")
                        
                        limpar_falha_acao(acao)
                        # Não limpa contexto se houver erros (para permitir análise)
                        if not resultado_validacao["tem_erros"]:
                            set_contexto(modo=None, dados_acao=None)
                    else:
                        falar_out(f"Erro ao aplicar: {resultado.get('message', 'Erro desconhecido')}")
                    continue

                # reverter_edicao_codigo: SEMPRE requer confirmação
                if acao == "reverter_edicao_codigo":
                    arquivo = dados.get("arquivo", "")
                    if not arquivo:
                        falar_out("Arquivo não informado.")
                        continue

                    # Pede confirmação explícita
                    set_contexto(
                        modo="reverter_edicao_pendente",
                        dados_acao={"acao": acao, "dados": dados}
                    )
                    falar_out(f"Tem certeza que quer reverter edições em {os.path.basename(arquivo)}? Digite 'sim' para confirmar.")
                    continue

            # Checa bloqueio de segurança
            bloqueio = acao_esta_bloqueada(acao)
            if bloqueio.get("data", {}).get("bloqueado"):
                falar_out("Essa ação está bloqueada por falhas consecutivas. Preciso de ensino manual.")
                continue

            # =============================
            # TRATAMENTO DE CONFIRMAÇÃO PARA REGISTRAR REGRA ARQUITETURAL
            # =============================
            if ctx.get("modo") == "registro_regra_pendente" and texto in confirmacoes:
                dados_pendentes = ctx.get("dados_acao", {})
                entrada = dados_pendentes.get("entrada", {})
                tipo_entrada = dados_pendentes.get("tipo", "regra")

                # Confirma e salva registro
                iniciar_execucao_acao("confirmar_registro_regra")
                logger.info("Confirmando registro de regra arquitetural.")
                resultado = executar_acao("confirmar_registro_regra", {
                    "entrada": entrada,
                    "tipo": tipo_entrada
                })
                concluir_execucao()

                if resultado.get("ok"):
                    falar_out(f"{tipo_entrada.capitalize()} salva na memória arquitetural!")
                    logger.info("Registro de %s salvo na memória arquitetural.", tipo_entrada)
                else:
                    msg_erro = resultado.get("mensagem", "Erro desconhecido")
                    falar_out(f"Erro ao salvar: {msg_erro}")
                    logger.error("Erro ao salvar %s na memória arquitetural: %s", tipo_entrada, msg_erro)

                set_contexto(modo=None, dados_acao=None)
                continue

            # =============================
            # TRATAMENTO DE CONFIRMAÇÃO PARA ANALISAR ERROS DE VALIDAÇÃO
            # =============================
            if ctx.get("modo") == "validacao_com_erros" and texto in confirmacoes:
                dados_pendentes = ctx.get("dados_acao", {})
                resultado_validacao = dados_pendentes.get("resultado_validacao", {})
                arquivo = dados_pendentes.get("arquivo", "")
                
                falar_out("Analisando erros e preparando correções...")
                
                # Prepara análise via IA (gera código corrigido)
                from yui_ai.code_editor.code_generator import analisar_e_sugerir_correcao
                
                # Monta descrição dos erros encontrados
                descricao_erros = []
                if not resultado_validacao.get("sintaxe", {}).get("sucesso"):
                    descricao_erros.append(f"Sintaxe: {resultado_validacao['sintaxe'].get('erro', 'Erro desconhecido')[:200]}")
                if not resultado_validacao.get("testes", {}).get("sucesso"):
                    detalhes = resultado_validacao.get("testes", {}).get("detalhes", {})
                    if detalhes.get("testes_executados", 0) > 0:
                        descricao_erros.append(f"Testes: {detalhes.get('testes_falharam', 0)} falharam")
                if not resultado_validacao.get("linter", {}).get("sucesso"):
                    detalhes = resultado_validacao.get("linter", {}).get("detalhes", {})
                    descricao_erros.append(f"Linter: {detalhes.get('erros', 0)} erros encontrados")
                
                descricao_completa = "Erros encontrados na validação:\n" + "\n".join(descricao_erros)
                
                # Gera correção via IA
                sucesso_analise, resultado_analise, erro_analise = analisar_e_sugerir_correcao(
                    arquivo,
                    descricao_completa
                )
                
                if sucesso_analise:
                    patch_correcao = resultado_analise.get("patch")
                    visualizacao_correcao = resultado_analise.get("visualizacao", "")
                    explicacao_correcao = resultado_analise.get("explicacao", "")
                    
                    # Mostra correção proposta
                    print_out("\n" + "="*60)
                    print_out(explicacao_correcao)
                    print_out("="*60 + "\n")
                    print_out(visualizacao_correcao)
                    
                    falar_out("Preparada correção para os erros encontrados. Posso aplicar?")
                    
                    # Salva correção no contexto
                    set_contexto(
                        modo="edicao_codigo_pendente",
                        dados_acao={
                            "acao": "aplicar_edicao_codigo",
                            "patch": patch_correcao,
                            "arquivo": arquivo
                        }
                    )
                else:
                    falar_out(f"Não consegui gerar correção automática: {erro_analise or 'Erro desconhecido'}")
                    set_contexto(modo=None, dados_acao=None)
                continue

            # =============================
            # TRATAMENTO DE CONFIRMAÇÃO PARA REVERTER EDIÇÃO
            # =============================
            if ctx.get("modo") == "reverter_edicao_pendente" and texto in confirmacoes:
                dados_pendentes = ctx.get("dados_acao", {})
                acao_reverter = dados_pendentes.get("acao")
                dados_reverter = dados_pendentes.get("dados", {})

                iniciar_execucao_acao(acao_reverter)
                resultado = executar_com_controle(acao_reverter, dados_reverter, executar_acao, falar_out)
                concluir_execucao()

                if resultado.get("status") == "ok":
                    falar_out("Edição revertida com sucesso.")
                    limpar_falha_acao(acao_reverter)
                else:
                    falar_out(f"Erro ao reverter: {resultado.get('message', 'Erro desconhecido')}")

                set_contexto(modo=None, dados_acao=None)
                continue

            # Atalhos DX e ações somente leitura / abertura de apps: execução direta, sem confirmação
            acoes_atalho_dx = [
                "abrir_aplicativo",
                "abrir_url",
                "pesquisar_no_navegador",
                "abrir_pasta_raiz",
                "mostrar_estrutura_projeto",
                "executar_validacao_completa",
                "abrir_logs",
                "consultar_memoria_arquitetural",
                "consultar_regras",
                "consultar_padroes",
                "obter_historico_edicoes",
                "executar_yui",
                "reiniciar_yui",
                "indexar_aplicativos",
                "atualizar_indice_aplicativos",
                "listar_aplicativos_indexados",
            ]
            if acao in acoes_atalho_dx:
                if acao in ("indexar_aplicativos", "atualizar_indice_aplicativos"):
                    falar_out("Indexando aplicativos (somente leitura)...")
                iniciar_execucao_acao(acao)
                resultado = executar_acao(acao, dados)
                concluir_execucao()
                ok = resultado.get("ok", False)
                if ok:
                    limpar_falha_acao(acao)
                    falar_out(resultado.get("mensagem", "Executado."))
                    data = resultado.get("dados", {})
                    if data.get("visualizacao"):
                        print_out(data["visualizacao"])
                    if data.get("relatorio"):
                        print_out(data["relatorio"])
                    if data.get("itens") is not None:
                        print_out("  " + "\n  ".join(str(x) for x in data["itens"]))
                else:
                    falar_out(resultado.get("mensagem", "Erro ao executar."))
                continue

            if pode_executar_sozinha(acao):
                iniciar_execucao_acao(acao)
                resultado = executar_com_controle(acao, dados, executar_acao, falar_out)
                concluir_execucao()

                if resultado.get("status") == "ok":
                    limpar_falha_acao(acao)
                    aumentar_autonomia()
            else:
                set_contexto(modo="acao_pendente", dados_acao={"acao": acao, "dados": dados})
                falar_out(f"Posso executar {acao}?")


if __name__ == "__main__":
    run()