import re

from yui_ai.core.file_resolver import normalizar_nome_arquivo

# =============================================================
# INTENT PARSER — YUI
# =============================================================

def _extrair_alvo_abrir(texto: str) -> str:
    """
    Extrai o alvo do comando de abrir, removendo artigos e frases de cortesia.
    Ex.: "abre o brave pra mim por favor" -> "brave"
    """
    alvo = (texto or "").strip()
    if not alvo:
        return ""

    # remove artigos/quantificadores no início
    alvo = re.sub(r"^(o|a|os|as|um|uma|uns|umas)\s+", "", alvo).strip()

    # remove frases de cortesia / complemento no final
    alvo = re.sub(
        r"\s+(por favor|por gentileza|pfv|porfa|pra mim|para mim|pra mim por favor|para mim por favor)\s*$",
        "",
        alvo
    ).strip()

    # remove sobras comuns no início
    alvo = re.sub(r"^(pra|para|pro|pra)\s+", "", alvo).strip()

    # normaliza espaços
    alvo = re.sub(r"\s{2,}", " ", alvo).strip()
    return alvo


def _limpar_caminho(texto: str) -> str:
    """
    Limpeza leve de caminho/alvo (mantém drive letters, barras e espaços).
    Remove aspas e palavras de cortesia no final.
    """
    s = (texto or "").strip().strip('"').strip("'").strip()
    if not s:
        return ""
    s = re.sub(r"\s+(por favor|por gentileza|pfv|porfa)\s*$", "", s).strip()
    return s


def interpretar_intencao(texto):
    texto_raw = (texto or "").strip()
    texto = texto_raw.lower().strip()

    if not texto:
        return _conversa()

    # =============================================================
    # 0. EDIÇÃO DE RESPOSTA ANTERIOR (não pede novo conteúdo)
    # =============================================================
    triggers_editar = [
        "altera isso", "altere isso", "muda aquilo", "mude aquilo",
        "ajusta a resposta", "ajuste a resposta", "ajusta aquela resposta",
        "melhora o código", "melhore o código", "melhora o codigo",
        "refatora o que você mandou", "refatore o que você mandou",
        "corrige o que você mandou", "corrija o que você mandou",
        "corrige a resposta", "corrija a resposta", "edita isso", "edite isso",
        "altera a resposta", "altere a resposta", "muda a resposta", "mude a resposta",
    ]
    for t in triggers_editar:
        if t in texto or texto.startswith(t):
            return {"tipo": "editar_resposta", "acao": None, "dados": {"pedido": texto_raw}, "nivel": 0}
    if re.search(r"^(altera|muda|ajusta|melhora|refatora|corrige|edita)\s+(isso|aquilo|a resposta)", texto):
        return {"tipo": "editar_resposta", "acao": None, "dados": {"pedido": texto_raw}, "nivel": 0}

    # =============================================================
    # 1. ENSINO NATURAL (PRIORIDADE MÁXIMA)
    # Ex: "navegador quer dizer abrir brave"
    # =============================================================
    ensino_patterns = [
        r"(.+?)\s+quer dizer\s+abrir\s+(.+)",
        r"(.+?)\s+significa\s+abrir\s+(.+)",
        r"quando eu pedir\s+(.+?)\s+abrir\s+(.+)",
        r"quando eu falar\s+(.+?)\s+abrir\s+(.+)"
    ]

    for pattern in ensino_patterns:
        match = re.search(pattern, texto)
        if match:
            gatilho = _limpar_gatilho(match.group(1))
            alvo = match.group(2).strip()

            if gatilho and alvo:
                return {
                    "tipo": "acao",
                    "acao": "salvar_macro",
                    "dados": {
                        "frase": gatilho,
                        "acoes": [
                            {
                                "acao": "abrir_qualquer_coisa",
                                "dados": {"alvo": alvo}
                            }
                        ]
                    },
                    "nivel": 0
                }

    # =============================================================
    # 2. MACRO COMPLEXA GUIADA
    # =============================================================
    if texto.startswith("quando eu disser") and "faça" in texto:
        try:
            frase = texto.replace("quando eu disser", "").split("faça")[0].strip()
            resto = texto.split("faça", 1)[1]

            acoes = []
            for parte in resto.split("abrir")[1:]:
                alvo = parte.split(" e ")[0].strip()
                if alvo:
                    acoes.append({
                        "acao": "abrir_qualquer_coisa",
                        "dados": {"alvo": alvo}
                    })

            if frase and acoes:
                return {
                    "tipo": "acao",
                    "acao": "salvar_macro",
                    "dados": {
                        "frase": _limpar_gatilho(frase),
                        "acoes": acoes
                    },
                    "nivel": 0
                }
        except Exception:
            pass

    # =============================================================
    # 3. COMANDO COMPOSTO (ABRIR + DIGITAR)
    # =============================================================
    if texto.startswith(("abrir", "abra")) and "digitar" in texto:
        match = re.search(
            r"(?:abrir|abra)\s+(.*?)\s+(?:e\s+)?digitar\s+(.*)",
            texto
        )
        if match:
            return {
                "tipo": "acao",
                "acao": "macro_dinamica",
                "dados": {
                    "acoes": [
                        {"acao": "abrir_qualquer_coisa", "dados": {"alvo": match.group(1).strip()}},
                        {"acao": "digitar_texto", "dados": {"texto": match.group(2).strip()}}
                    ]
                },
                "nivel": 3
            }

    # =============================================================
    # 4. IDENTIDADE / MEMÓRIA
    # =============================================================
    if texto.startswith(("meu nome é", "o nome é")):
        nome = texto.replace("meu nome é", "").replace("o nome é", "").strip()
        return _acao("salvar_nome", {"nome": nome})

    if texto.startswith(("lembra que", "lembre que")):
        conteudo = texto.replace("lembra que", "").replace("lembre que", "").strip()
        return _acao("salvar_memoria", {"conteudo": conteudo})

    # =============================================================
    # 5. ARQUIVOS / PASTAS (WINDOWS)
    # =============================================================
    # listar arquivos em <pasta>
    match = re.search(r"^(listar|mostra|mostrar)\s+(arquivos|itens)\s+(em|da|do|na|no)\s+(.+)$", texto)
    if match:
        caminho = _limpar_caminho(match.group(4))
        return _acao("listar_diretorio", {"caminho": caminho, "limite": 20}, 1)

    # criar pasta <caminho>
    match = re.search(r"^(criar|crie|cria|nova)\s+pasta\s+(.+)$", texto)
    if match:
        caminho = _limpar_caminho(match.group(2))
        return _acao("criar_pasta", {"caminho": caminho}, 2)

    # mover <origem> para <destino>
    match = re.search(r"^(mover|mova)\s+(.+?)\s+para\s+(.+)$", texto)
    if match:
        origem = _limpar_caminho(match.group(2))
        destino = _limpar_caminho(match.group(3))
        return _acao("mover_caminho", {"origem": origem, "destino": destino}, 2)

    # copiar <origem> para <destino>
    match = re.search(r"^(copiar|copia)\s+(.+?)\s+para\s+(.+)$", texto)
    if match:
        origem = _limpar_caminho(match.group(2))
        destino = _limpar_caminho(match.group(3))
        return _acao("copiar_caminho", {"origem": origem, "destino": destino}, 2)

    # excluir/deletar/apagar <caminho> (opcional: definitivamente)
    match = re.search(r"^(excluir|deletar|apagar)\s+(.+)$", texto)
    if match:
        restante = match.group(2).strip()
        definitivo = False
        if "definitiv" in restante:
            definitivo = True
            restante = re.sub(r"\bdefinitiv\w*\b", "", restante).strip()
        caminho = _limpar_caminho(restante)
        return _acao("excluir_caminho", {"caminho": caminho, "definitivo": definitivo}, 3)

    # renomear <origem> para <novo>
    match = re.search(r"^(renomear|renomeia)\s+(.+?)\s+para\s+(.+)$", texto)
    if match:
        origem = _limpar_caminho(match.group(2))
        novo = _limpar_caminho(match.group(3))
        return _acao("renomear_caminho", {"origem": origem, "novo": novo}, 2)

    # ler arquivo <caminho>
    match = re.search(r"^(ler|mostra|mostrar|exibir)\s+(arquivo|texto)\s+(.+)$", texto)
    if match:
        caminho = _limpar_caminho(match.group(3))
        return _acao("ler_arquivo_texto", {"caminho": caminho, "max_chars": 4000}, 1)

    # escrever arquivo <caminho>: <texto>
    match = re.search(r"^(escrever|escreve)\s+arquivo\s+(.+?)(?:\:|\s+com\s+)\s+(.+)$", texto)
    if match:
        caminho = _limpar_caminho(match.group(2))
        conteudo = match.group(3).strip()
        return _acao("escrever_arquivo_texto", {"caminho": caminho, "texto": conteudo, "modo": "sobrescrever"}, 2)

    # anexar em <caminho>: <texto>
    match = re.search(r"^(anexar|adicionar)\s+em\s+(.+?)(?:\:|\s+)\s+(.+)$", texto)
    if match:
        caminho = _limpar_caminho(match.group(2))
        conteudo = match.group(3).strip()
        return _acao("escrever_arquivo_texto", {"caminho": caminho, "texto": conteudo, "modo": "anexar"}, 2)

    # buscar arquivos <padrao> em <pasta>
    match = re.search(r"^(buscar|procurar)\s+arquivos\s+(.+?)\s+(?:em|na|no|dentro de)\s+(.+)$", texto)
    if match:
        padrao = _limpar_caminho(match.group(2))
        pasta = _limpar_caminho(match.group(3))
        return _acao("buscar_arquivos", {"pasta": pasta, "padrao": padrao, "limite": 50}, 1)

    # compactar <origem> em <zip>
    match = re.search(r"^(compactar|zipar)\s+(.+?)\s+(?:em|para)\s+(.+)$", texto)
    if match:
        origem = _limpar_caminho(match.group(2))
        destino = _limpar_caminho(match.group(3))
        return _acao("compactar_zip", {"origem": origem, "destino": destino}, 2)

    # extrair <zip> em <pasta>
    match = re.search(r"^(extrair|descompactar)\s+(.+?)\s+(?:em|para)\s+(.+)$", texto)
    if match:
        zpath = _limpar_caminho(match.group(2))
        destino = _limpar_caminho(match.group(3))
        return _acao("extrair_zip", {"zip": zpath, "destino": destino}, 2)

    # listar processos
    if texto in ["listar processos", "processos", "mostrar processos"]:
        return _acao("listar_processos", {"limite": 30}, 1)

    # fechar/encerrar processo
    match = re.search(r"^(fechar|encerrar|matar)\s+(processo\s+)?(.+)$", texto)
    if match and any(k in texto for k in ["processo", "fechar", "encerrar", "matar"]):
        ident = _limpar_caminho(match.group(3))
        return _acao("encerrar_processo", {"identificador": ident, "forcar": True}, 3)

    # abrir arquivo/pasta explicitamente (senão cai no abrir genérico)
    match = re.search(r"^(abrir|abre|abra)\s+(arquivo|pasta|diret[óo]rio)\s+(.+)$", texto)
    if match:
        caminho = _limpar_caminho(match.group(3))
        return _acao("abrir_caminho", {"caminho": caminho}, 1)

    # =============================================================
    # 5.4. MEMÓRIA ARQUITETURAL E REGRAS (NÍVEL 2)
    # =============================================================
    
    # registrar regra: <regra>
    match = re.search(r"^(registrar|registre|adicionar|adiciona)\s+(?:regra|padrão|padrao|restrição|restricao|decisão|decisao)\s*:\s*(.+)$", texto)
    if match:
        tipo = match.group(1)
        conteudo = match.group(2).strip()
        return _acao("registrar_regra_arquitetural", {
            "comando_completo": f"{tipo}: {conteudo}",
            "tipo": tipo,
            "conteudo": conteudo
        }, 2)
    
    # consultar regras/padrões
    if texto in ["mostrar regras", "regras do projeto", "listar regras"]:
        return _acao("consultar_regras", {"filtro": ""}, 1)
    
    if texto in ["mostrar padrões", "padrões do projeto", "listar padrões"]:
        return _acao("consultar_padroes", {"filtro": ""}, 1)
    
    if texto in ["mostrar memória arquitetural", "memória arquitetural", "arquitetura do projeto"]:
        return _acao("consultar_memoria_arquitetural", {}, 1)

    # =============================================================
    # ANÁLISE DE PROJETO (SOMENTE LEITURA — NÍVEL 1, SEM CONFIRMAÇÃO)
    # =============================================================
    if texto in [
        "analisa o projeto",
        "analisar projeto",
        "analise o projeto",
        "faça uma análise da arquitetura",
        "fazer análise da arquitetura",
        "análise da arquitetura",
        "o que pode melhorar nesse projeto",
        "o que pode melhorar neste projeto",
        "gere um roadmap de melhorias",
        "gerar roadmap de melhorias",
        "roadmap de melhorias",
        "diagnóstico técnico do projeto",
        "diagnóstico do projeto",
        "relatório do projeto",
    ]:
        return _acao("analisar_projeto", {"raiz": ""}, 1)
    if re.search(r"^(analisa|analise|analisar)\s+(o\s+)?projeto$", texto):
        return _acao("analisar_projeto", {"raiz": ""}, 1)
    if re.search(r"^(faça|fazer|faz)\s+(uma\s+)?an[aá]lise\s+(da\s+)?(arquitetura|estrutura)", texto):
        return _acao("analisar_projeto", {"raiz": ""}, 1)
    if re.search(r"^(gere|gerar|gera)\s+(um\s+)?roadmap", texto):
        return _acao("analisar_projeto", {"raiz": ""}, 1)
    if re.search(r"diagn[oó]stico\s+(t[eé]cnico\s+)?(do\s+)?projeto", texto):
        return _acao("analisar_projeto", {"raiz": ""}, 1)

    # =============================================================
    # ATALHOS DX (ABRIR PROJETO, ESTRUTURA, VALIDAÇÃO, LOGS, ETC.)
    # =============================================================
    if texto in ["abrir projeto", "abrir pasta raiz", "abrir raiz", "abrir pasta do projeto"]:
        return _acao("abrir_pasta_raiz", {}, 1)
    if texto in ["mostrar estrutura do projeto", "estrutura do projeto", "listar estrutura", "mostrar estrutura"]:
        return _acao("mostrar_estrutura_projeto", {"limite": 50}, 1)
    if texto in ["executar validação completa", "validação completa", "rodar validação", "validar projeto"]:
        return _acao("executar_validacao_completa", {}, 1)
    if texto in ["abrir logs", "mostrar logs", "pasta de logs"]:
        return _acao("abrir_logs", {}, 1)
    if texto in ["abrir memória arquitetural", "abrir memória da arquitetura", "ver memória arquitetural"]:
        return _acao("consultar_memoria_arquitetural", {}, 1)
    if texto in ["abrir histórico de edições", "histórico de edições", "mostrar histórico de edições"]:
        return _acao("obter_historico_edicoes", {"arquivo": None, "limite": 10}, 1)
    if texto in ["executar yui", "rodar yui", "iniciar yui"]:
        return _acao("executar_yui", {}, 1)
    if texto in ["reiniciar yui", "reiniciar a yui"]:
        return _acao("reiniciar_yui", {}, 1)
    # Indexação de aplicativos (somente leitura)
    if texto in ["indexar aplicativos", "indexar apps", "criar índice de aplicativos"]:
        return _acao("indexar_aplicativos", {}, 1)
    if texto in ["atualizar lista de aplicativos", "atualizar índice de aplicativos", "atualizar aplicativos", "atualizar índice"]:
        return _acao("atualizar_indice_aplicativos", {}, 1)
    # Listar aplicativos com filtro por nome: "listar aplicativos com chrome", "aplicativos que tenham code"
    match = re.search(
        r"^(listar|mostrar|ver)\s+(?:lista\s+de\s+)?aplicativos\s+(?:com|que\s+tenham|com\s+nome)\s+(.+)$",
        texto,
    )
    if match:
        filtro = match.group(2).strip()
        return _acao("listar_aplicativos_indexados", {"filtro_nome": filtro}, 1)
    match = re.search(
        r"^aplicativos\s+(?:instalados\s+)?(?:que\s+tenham|com)\s+(.+)$",
        texto,
    )
    if match:
        return _acao("listar_aplicativos_indexados", {"filtro_nome": match.group(1).strip()}, 1)
    # Listar aplicativos ordenados por: "listar aplicativos por tamanho", "mostrar apps por nome"
    match = re.search(
        r"^(listar|mostrar|ver)\s+(?:lista\s+de\s+)?(?:aplicativos|apps)\s+por\s+(nome|tamanho|origem|tipo)\s*$",
        texto,
    )
    if match:
        return _acao("listar_aplicativos_indexados", {"ordenar_por": match.group(2)}, 1)
    # Listar com filtro e ordenação: "listar aplicativos com chrome por tamanho"
    match = re.search(
        r"^(listar|mostrar)\s+(?:aplicativos|apps)\s+com\s+(.+?)\s+por\s+(nome|tamanho|origem|tipo)\s*$",
        texto,
    )
    if match:
        return _acao("listar_aplicativos_indexados", {
            "filtro_nome": match.group(2).strip(),
            "ordenar_por": match.group(3),
        }, 1)
    if texto in ["listar aplicativos", "mostrar aplicativos instalados", "aplicativos instalados", "listar apps", "mostrar apps", "lista de aplicativos", "mostrar lista de aplicativos"]:
        return _acao("listar_aplicativos_indexados", {}, 1)

    # =============================================================
    # 5.5. EDIÇÃO DE CÓDIGO (REQUER CONFIRMAÇÃO - NÍVEL 3)
    # Foco principal: correção de código e criação/melhoria de APIs.
    # Tolerante à linguagem natural; nunca falha silenciosamente.
    # =============================================================

    # ----- Criar endpoint REST: "cria endpoint GET /usuarios no arquivo api.py"
    match = re.search(
        r"^(criar|cria|gera|gerar)\s+(?:um\s+)?endpoint\s+"
        r"(get|post|put|delete|patch)\s+([^\s]+)\s+(?:no|em|do|da)\s+(.+)$",
        texto,
    )
    if match:
        metodo = match.group(2).upper()
        rota = match.group(3).strip()
        arquivo = normalizar_nome_arquivo(_limpar_caminho(match.group(4)))
        if arquivo:
            instrucao = (
                f"Criar endpoint {metodo} {rota} nesta API, seguindo boas práticas de REST, "
                f"tratamento de erros, respostas padronizadas e documentação mínima."
            )
            contexto_adicional = (
                "Se o arquivo já usa algum framework web (por exemplo FastAPI, Flask, Django, "
                "ou outro), siga o mesmo estilo e padrões existentes no código."
            )
            return _acao(
                "gerar_codigo_refatorado",
                {
                    "arquivo": arquivo,
                    "instrucao": instrucao,
                    "contexto_adicional": contexto_adicional,
                },
                3,
            )
        return _esclarecer("Em qual arquivo você quer criar o endpoint? Exemplo: criar endpoint GET /usuarios no arquivo api.py")

    # ----- Criar rota simples: "adiciona rota /usuarios no arquivo api.py" (assume GET)
    match = re.search(
        r"^(adicionar|adiciona|criar|cria|gerar)\s+(?:uma\s+)?rota\s+([^\s]+)\s+(?:no|em|do|da)\s+(.+)$",
        texto,
    )
    if match:
        rota = match.group(2).strip()
        arquivo = normalizar_nome_arquivo(_limpar_caminho(match.group(3)))
        if arquivo:
            instrucao = (
                f"Criar rota GET {rota} nesta API, organizando o handler de forma clara, "
                f"com validação básica de entrada (se necessário) e respostas padronizadas."
            )
            contexto_adicional = (
                "Respeite o estilo e o framework já usados no arquivo (por exemplo, FastAPI, Flask, Django)."
            )
            return _acao(
                "gerar_codigo_refatorado",
                {
                    "arquivo": arquivo,
                    "instrucao": instrucao,
                    "contexto_adicional": contexto_adicional,
                },
                3,
            )
        return _esclarecer("Em qual arquivo você quer adicionar a rota? Exemplo: adicionar rota /usuarios no arquivo api.py")

    # ----- Corrigir/ajustar código de um arquivo (não só bug): "corrige código do arquivo X"
    match = re.search(
        r"^(corrigir|corrige|corrija)\s+(?:c[oó]digo|arquivo)\s+(.+)$",
        texto,
    )
    if match:
        arquivo = normalizar_nome_arquivo(_limpar_caminho(match.group(2)))
        if arquivo:
            instrucao = (
                "Corrigir e melhorar o código deste arquivo, incluindo correção de bugs óbvios, "
                "melhoria de legibilidade, extração de funções quando fizer sentido e aplicação "
                "de boas práticas (tratamento de erros, nomes claros, organização por responsabilidade)."
            )
            return _acao(
                "gerar_codigo_refatorado",
                {
                    "arquivo": arquivo,
                    "instrucao": instrucao,
                    "contexto_adicional": "",
                },
                3,
            )
        return _esclarecer("Qual arquivo você quer corrigir? Exemplo: corrige código api.py")

    # ----- Melhorar API de um arquivo: "melhora a API do arquivo api.py"
    match = re.search(
        r"^(melhorar|melhora|otimizar|otimiza|refatorar\s+api)\s+(?:a\s+)?(?:api|rota|endpoint)s?\s+(?:no|em|do|da)\s+(.+)$",
        texto,
    )
    if match:
        alvo_arquivo = match.group(1) if match.group(1) else ""
        arquivo_raw = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(match.lastindex or 1)
        arquivo = normalizar_nome_arquivo(_limpar_caminho(arquivo_raw))
        if arquivo:
            instrucao = (
                "Refatorar e melhorar a API (rotas, handlers, validação e respostas) "
                "deste arquivo, mantendo o comportamento atual, mas deixando o código "
                "mais organizado, legível e alinhado com boas práticas REST."
            )
            contexto_adicional = (
                "Mantenha nomes de rotas e contratos de entrada/saída compatíveis com o código atual, "
                "apenas melhorando a estrutura interna."
            )
            return _acao(
                "gerar_codigo_refatorado",
                {
                    "arquivo": arquivo,
                    "instrucao": instrucao,
                    "contexto_adicional": contexto_adicional,
                },
                3,
            )
        return _esclarecer("Em qual arquivo está a API que você quer melhorar? Exemplo: melhorar api no arquivo api.py")

    # ----- Linguagem natural: "refatora uma função simples no arquivo utils.py"
    match = re.search(
        r"^(refatorar|refatora|refatore)\s+.+?\s+(?:no\s+)?(?:arquivo\s+)?(?:no|em|do|da)\s+(.+)$",
        texto,
    )
    if match:
        arquivo_raw = match.group(2).strip()
        arquivo = normalizar_nome_arquivo(arquivo_raw)
        if arquivo:
            return _acao("gerar_codigo_refatorado", {
                "arquivo": arquivo,
                "instrucao": "Refatorar código para melhorar legibilidade e estrutura",
                "contexto_adicional": "",
            }, 3)
        return _esclarecer("Não consegui identificar o arquivo. Pode dizer de novo, por exemplo: refatorar no arquivo utils.py?")

    # ----- "refatora o arquivo utils.py" / "refatora arquivo utils.py"
    match = re.search(r"^(refatorar|refatora|refatore)\s+(?:o\s+)?arquivo\s+(.+)$", texto)
    if match:
        arquivo = normalizar_nome_arquivo(match.group(2))
        if arquivo:
            return _acao("gerar_codigo_refatorado", {
                "arquivo": arquivo,
                "instrucao": "Refatorar código para melhorar legibilidade e estrutura",
                "contexto_adicional": "",
            }, 3)
        return _esclarecer("Qual arquivo você quer refatorar? Exemplo: refatorar arquivo utils.py")

    # ----- "corrige bug em utils.py" / "corrige bug no arquivo utils.py"
    match = re.search(
        r"^(corrigir|corrige|corrija)\s+(?:bug|erro|problema)\s+(?:no\s+)?(?:arquivo\s+)?(?:no|em|do|da)\s+(.+)$",
        texto,
    )
    if match:
        arquivo = normalizar_nome_arquivo(match.group(2))
        if arquivo:
            return _acao("analisar_e_corrigir_bug", {
                "arquivo": arquivo,
                "descricao_bug": "",
            }, 3)
        return _esclarecer("Em qual arquivo está o bug? Exemplo: corrige bug em utils.py")

    # ----- "arruma utils.py" (tratado como corrigir)
    match = re.search(r"^(arruma|arrumar|conserta|consertar)\s+(.+)$", texto)
    if match:
        arquivo = normalizar_nome_arquivo(match.group(2))
        if arquivo:
            return _acao("analisar_e_corrigir_bug", {
                "arquivo": arquivo,
                "descricao_bug": "",
            }, 3)
        return _esclarecer("Qual arquivo você quer que eu arrume? Exemplo: arruma utils.py")

    # ----- Refatorar só nome de arquivo no final: "refatora utils.py"
    match = re.search(r"^(refatorar|refatora|refatore)\s+(.+)$", texto)
    if match:
        segundo = match.group(2).strip()
        # Evita capturar "função X" como arquivo
        if "função" not in segundo and "classe" not in segundo and "método" not in segundo:
            arquivo = normalizar_nome_arquivo(segundo)
            if arquivo and ("." in arquivo or "/" in arquivo or "\\" in arquivo):
                return _acao("gerar_codigo_refatorado", {
                    "arquivo": arquivo,
                    "instrucao": "Refatorar código para melhorar legibilidade e estrutura",
                    "contexto_adicional": "",
                }, 3)

    # refatorar função/classe em arquivo
    match = re.search(r"^(refatorar|refatora|refatore)\s+(?:fun[çc][ãa]o|classe|m[ée]todo)\s+(\w+)\s+(?:no|em|do|da)\s+(.+)$", texto)
    if match:
        nome_item = match.group(2)
        arquivo = normalizar_nome_arquivo(_limpar_caminho(match.group(3)))
        if arquivo:
            return _acao("gerar_codigo_refatorado", {
                "arquivo": arquivo,
                "instrucao": f"Refatorar {nome_item}",
                "contexto_adicional": f"Foque na função/classe/método '{nome_item}'."
            }, 3)
        return _esclarecer("Em qual arquivo está a função/classe que você quer refatorar?")

    # refatorar arquivo inteiro
    match = re.search(r"^(refatorar|refatora|refatore)\s+(.+)$", texto)
    if match and not any(x in match.group(2) for x in ["função", "classe", "método"]):
        arquivo = normalizar_nome_arquivo(_limpar_caminho(match.group(2)))
        if arquivo:
            return _acao("gerar_codigo_refatorado", {
                "arquivo": arquivo,
                "instrucao": "Refatorar código para melhorar legibilidade e estrutura",
                "contexto_adicional": ""
            }, 3)
        return _esclarecer("Qual arquivo você quer refatorar? Exemplo: refatora utils.py")

    # corrigir bug em arquivo
    match = re.search(r"^(corrigir|corrige|corrija)\s+(?:bug|erro|problema)\s+(?:no|em|do|da)\s+(.+)$", texto)
    if match:
        arquivo = normalizar_nome_arquivo(_limpar_caminho(match.group(2)))
        if arquivo:
            return _acao("analisar_e_corrigir_bug", {
                "arquivo": arquivo,
                "descricao_bug": ""
            }, 3)
        return _esclarecer("Em qual arquivo está o bug? Exemplo: corrige bug em utils.py")

    # corrigir bug específico
    match = re.search(r"^(corrigir|corrige|corrija)\s+(.+?)\s+(?:no|em|do|da)\s+(.+)$", texto)
    if match:
        descricao = match.group(2).strip()
        arquivo = normalizar_nome_arquivo(_limpar_caminho(match.group(3)))
        if arquivo:
            return _acao("analisar_e_corrigir_bug", {
                "arquivo": arquivo,
                "descricao_bug": descricao
            }, 3)
        return _esclarecer("Em qual arquivo? Exemplo: corrige o erro X no arquivo utils.py")
    
    # visualizar edições pendentes
    if texto in ["mostrar edições pendentes", "edições pendentes", "mudanças pendentes"]:
        return _acao("visualizar_edicoes_pendentes", {}, 1)
    
    # histórico de edições
    match = re.search(r"^(hist[óo]rico|mostrar hist[óo]rico)\s+(?:de\s+)?(?:edi[çc][õo]es\s+)?(?:em\s+)?(.+)?$", texto)
    if match:
        arquivo = match.group(2).strip() if match.group(2) else None
        return _acao("obter_historico_edicoes", {"arquivo": _limpar_caminho(arquivo) if arquivo else None, "limite": 10}, 1)
    
    # reverter edição
    match = re.search(r"^(reverter|desfazer|undo)\s+(?:edi[çc][ãa]o\s+)?(?:em\s+)?(.+)$", texto)
    if match:
        arquivo = _limpar_caminho(match.group(2))
        return _acao("reverter_edicao_codigo", {"arquivo": arquivo}, 3)

    # =============================================================
    # 6. MOUSE
    # =============================================================
    if "mouse" in texto:
        distancia = 300
        if "bem pouco" in texto: distancia = 50
        elif "pouco" in texto: distancia = 150
        elif "muito" in texto or "mais" in texto: distancia = 600

        for direcao in ["esquerda", "direita", "cima", "baixo", "centro"]:
            if direcao in texto:
                return {
                    "tipo": "acao",
                    "acao": "mover_mouse_centro" if direcao == "centro" else "mover_mouse_direcao",
                    "dados": {"direcao": direcao, "distancia": distancia},
                    "nivel": 3
                }

    # =============================================================
    # 7. TECLADO
    # =============================================================
    if texto.startswith("digitar"):
        return _acao("digitar_texto", {"texto": texto.replace("digitar", "").strip()}, 3)

    if texto in ["pressionar enter", "dar enter", "dá enter"]:
        return _acao("pressionar_tecla", {"tecla": "enter"}, 3)

    # =============================================================
    # 7.5. NAVEGADOR: PESQUISAR E ABRIR SITE
    # =============================================================
    if texto.startswith(("pesquisar ", "pesquisa ", "buscar ", "busca ")):
        termo = re.sub(r"^(pesquisar|pesquisa|buscar|busca)\s+", "", texto).strip()
        if termo:
            return _acao("pesquisar_no_navegador", {"termo": termo}, 1)
        return _esclarecer("O que você quer pesquisar? Exemplo: pesquisar clima em São Paulo.")
    if texto.startswith(("entrar em ", "entra em ", "abrir site ", "abre site ", "abrir no navegador ", "abre no navegador ")):
        prefixos = r"^(?:entrar em|entra em|abrir site|abre site|abrir no navegador|abre no navegador)\s+"
        site = re.sub(prefixos, "", texto).strip().strip('"').strip("'")
        if site:
            return _acao("abrir_url", {"url": site}, 1)
        return _esclarecer("Qual site você quer abrir? Exemplo: entrar em google.com")
    if re.match(r"^ir (?:para|em)\s+.+", texto):
        site = re.sub(r"^ir (?:para|em)\s+", "", texto).strip().strip('"').strip("'")
        if site:
            return _acao("abrir_url", {"url": site}, 1)

    # =============================================================
    # 8. ABRIR APLICATIVO (engine profissional — sem confirmação)
    # =============================================================
    if texto.startswith(("abrir ", "abre ", "abra ")):
        match = re.search(r"^(?:abrir|abre|abra)\s+(.*)$", texto)
        alvo_bruto = match.group(1).strip() if match else ""
        alvo = _extrair_alvo_abrir(alvo_bruto)
        if alvo:
            return _acao("abrir_aplicativo", {"nome_aplicativo": alvo}, 1)
        return _esclarecer("Qual aplicativo você quer abrir? Exemplo: abrir chrome")

    # =============================================================
    # 9. CONVERSA
    # =============================================================
    return _conversa()


# =============================================================
# HELPERS
# =============================================================

def _limpar_gatilho(texto):
    lixo = ["abrir", "para", "o", "a"]
    for l in lixo:
        texto = texto.replace(l, "")
    return texto.strip()


def _acao(nome, dados=None, nivel=0):
    return {
        "tipo": "acao",
        "acao": nome,
        "dados": dados or {},
        "nivel": nivel
    }


def _conversa():
    return {
        "tipo": "conversa",
        "acao": None,
        "dados": {},
        "nivel": 0
    }


def _esclarecer(mensagem: str):
    """Retorno quando a intenção é ambígua ou incompleta. Nunca falhar silenciosamente."""
    return {
        "tipo": "esclarecer",
        "acao": None,
        "dados": {"mensagem": mensagem},
        "nivel": 0
    }
