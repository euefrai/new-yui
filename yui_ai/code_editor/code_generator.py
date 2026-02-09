"""
Gerador de código via IA com segurança obrigatória.

REGRAS OBRIGATÓRIAS:
1. NUNCA aplica código diretamente
2. SEMPRE gera diff e prepara edição
3. SEMPRE explica o que/por quê/quais arquivos
4. SEMPRE requer confirmação explícita
"""

import os
from typing import Dict, Optional, Tuple
from yui_ai.core.ai_engine import perguntar_yui
from yui_ai.actions.code_actions import preparar_edicao_codigo


def gerar_codigo_refatorado(
    arquivo: str,
    instrucao: str,
    contexto_adicional: str = ""
) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Gera código refatorado via IA e prepara edição.

    NUNCA aplica diretamente - sempre prepara edição para confirmação.

    Retorna: (sucesso, resultado, mensagem_erro)
    resultado = {
        "patch": dict,  # patch preparado
        "visualizacao": str,  # diff visualizado
        "explicacao": str,  # o que/por quê/quais arquivos
        "arquivo": str
    }
    """
    arquivo_abs = os.path.abspath(arquivo)

    if not os.path.exists(arquivo_abs):
        return False, None, f"Arquivo não encontrado: {arquivo_abs}"

    if os.path.isdir(arquivo_abs):
        return False, None, f"Caminho é uma pasta, não um arquivo: {arquivo_abs}"

    try:
        # 1. Lê conteúdo atual
        with open(arquivo_abs, "r", encoding="utf-8", errors="replace") as f:
            conteudo_atual = f.read()

        # 2. Consulta memória arquitetural ANTES de gerar código
        contexto_arquitetural = ""
        try:
            from yui_ai.architecture.memory_store import ArchitectureMemory
            memory = ArchitectureMemory()
            contexto_arquitetural = memory.montar_contexto_arquitetural(arquivo_abs, instrucao)
        except Exception:
            pass

        # 3. Monta prompt incluindo contexto arquitetural
        prompt = _montar_prompt_refatoracao(
            arquivo_abs,
            conteudo_atual,
            instrucao,
            contexto_adicional,
            contexto_arquitetural
        )

        # 3. Gera código novo via IA
        resposta_ia = perguntar_yui(prompt, None)

        if not resposta_ia or resposta_ia.get("status") != "ok":
            return False, None, "Falha ao gerar código via IA"

        # 4. Extrai código novo da resposta
        dados_resposta = resposta_ia.get("data", {})
        conteudo_novo = _extrair_codigo_da_resposta(dados_resposta, conteudo_atual)

        if not conteudo_novo:
            return False, None, "Não foi possível extrair código da resposta da IA"

        # 5. Gera explicação (inclui regras relevantes)
        explicacao = _gerar_explicacao(dados_resposta, arquivo_abs, instrucao, contexto_arquitetural or "")

        # 6. Prepara edição (NÃO APLICA)
        resultado_preparacao = preparar_edicao_codigo(
            arquivo_abs,
            conteudo_novo,
            f"Refatoração: {instrucao}"
        )

        if not resultado_preparacao.get("ok"):
            return False, None, resultado_preparacao.get("mensagem", "Falha ao preparar edição")

        # 7. Monta resultado completo
        resultado = {
            "patch": resultado_preparacao["dados"]["patch"],
            "visualizacao": resultado_preparacao["dados"]["visualizacao"],
            "explicacao": explicacao,
            "arquivo": arquivo_abs,
            "conteudo_antigo": conteudo_atual,
            "conteudo_novo": conteudo_novo
        }

        return True, resultado, None

    except Exception as e:
        return False, None, str(e)


def _montar_prompt_refatoracao(
    arquivo: str,
    conteudo_atual: str,
    instrucao: str,
    contexto_adicional: str = "",
    contexto_arquitetural: str = ""
) -> str:
    """
    Monta prompt estruturado para refatoração via IA.

    Recebe contexto_arquitetural como parâmetro (já consultado antes).
    """
    nome_arquivo = os.path.basename(arquivo)
    extensao = os.path.splitext(nome_arquivo)[1]

    prompt = f"""Você é um assistente de refatoração de código especializado.

TAREFA: {instrucao}

ARQUIVO: {nome_arquivo} ({extensao})

{contexto_arquitetural if contexto_arquitetural else ""}

CÓDIGO ATUAL:
```
{conteudo_atual}
```

{contexto_adicional}

INSTRUÇÕES:
1. Analise o código atual
2. RESPEITE as regras e padrões arquiteturais do projeto listados acima
3. Aplique a refatoração solicitada
4. Mantenha funcionalidade existente
5. Melhore legibilidade e estrutura seguindo os padrões do projeto
6. Retorne APENAS o código completo refatorado (sem explicações no meio do código)
7. Se a refatoração não for possível, retorne o código original sem mudanças

FORMATO DE RESPOSTA:
Retorne o código refatorado completo, pronto para substituir o arquivo inteiro.
Não adicione comentários explicativos dentro do código.
Se precisar explicar algo, faça ANTES ou DEPOIS do código.

CÓDIGO REFATORADO:"""

    return prompt


def _extrair_codigo_da_resposta(
    dados_resposta: dict,
    conteudo_original: str
) -> Optional[str]:
    """
    Extrai código novo da resposta da IA.

    Tenta múltiplas estratégias:
    1. Procura por blocos de código (```)
    2. Procura por resposta direta
    3. Fallback: retorna original se não conseguir extrair
    """
    resposta_texto = dados_resposta.get("resposta", "")

    if not resposta_texto:
        return None

    # Estratégia 1: Bloco de código com ```
    if "```" in resposta_texto:
        partes = resposta_texto.split("```")
        for i, parte in enumerate(partes):
            if i % 2 == 1:  # partes ímpares são código
                linhas = parte.split("\n")
                # Remove primeira linha se for nome da linguagem
                if len(linhas) > 1 and linhas[0].strip() in ["python", "py", "javascript", "js", "typescript", "ts"]:
                    linhas = linhas[1:]
                codigo = "\n".join(linhas).strip()
                if codigo:
                    return codigo

    # Estratégia 2: Resposta direta (assume que é código)
    resposta_limpa = resposta_texto.strip()
    if resposta_limpa and len(resposta_limpa) > 10:
        # Validação básica: tem pelo menos algumas linhas ou estrutura mínima
        linhas = resposta_limpa.split("\n")
        if len(linhas) >= 2 or any(c in resposta_limpa for c in ["def ", "class ", "import ", "function ", "const ", "let "]):
            return resposta_limpa

    # Fallback: retorna original (não conseguiu extrair)
    return conteudo_original


def _gerar_explicacao(
    dados_resposta: dict,
    arquivo: str,
    instrucao: str,
    contexto_arquitetural: str = ""
) -> str:
    """
    Gera explicação do que foi mudado e por quê.

    Inclui menção a regras relevantes se houver.
    """
    resposta_texto = dados_resposta.get("resposta", "")
    nome_arquivo = os.path.basename(arquivo)

    # Tenta extrair explicação da resposta da IA
    explicacao_partes = []

    # Se tem explicação antes do código
    if "```" in resposta_texto:
        antes_codigo = resposta_texto.split("```")[0].strip()
        if antes_codigo:
            explicacao_partes.append(antes_codigo)

    # Se tem explicação depois do código
    if "```" in resposta_texto:
        partes = resposta_texto.split("```")
        if len(partes) > 2:
            depois_codigo = partes[-1].strip()
            if depois_codigo:
                explicacao_partes.append(depois_codigo)

    # Monta explicação estruturada
    explicacao = f"📝 Refatoração em {nome_arquivo}\n"
    explicacao += f"📋 Instrução: {instrucao}\n\n"

    # Menciona regras relevantes se houver contexto arquitetural
    if contexto_arquitetural:
        regras_obrigatorias = []
        for linha in contexto_arquitetural.split("\n"):
            if linha.strip().startswith("- ") and "REGRAS OBRIGATÓRIAS" in contexto_arquitetural:
                regras_obrigatorias.append(linha.strip()[2:])  # Remove "- "
        
        if regras_obrigatorias:
            explicacao += "📐 Regras do projeto aplicadas:\n"
            for regra in regras_obrigatorias[:3]:  # Máximo 3 regras
                explicacao += f"  • {regra}\n"
            explicacao += "\n"

    if explicacao_partes:
        explicacao += "💡 Explicação da IA:\n"
        explicacao += "\n".join(explicacao_partes)
    else:
        explicacao += "💡 Código refatorado conforme solicitado.\n"
        explicacao += "Revise o diff abaixo para ver as mudanças."

    return explicacao


def analisar_e_sugerir_correcao(
    arquivo: str,
    descricao_bug: str = ""
) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Analisa código e sugere correção de bug.

    NUNCA aplica diretamente - sempre prepara edição para confirmação.
    """
    arquivo_abs = os.path.abspath(arquivo)

    if not os.path.exists(arquivo_abs):
        return False, None, f"Arquivo não encontrado: {arquivo_abs}"

    try:
        with open(arquivo_abs, "r", encoding="utf-8", errors="replace") as f:
            conteudo_atual = f.read()

        prompt = f"""Você é um assistente de correção de bugs.

ARQUIVO: {os.path.basename(arquivo_abs)}

CÓDIGO ATUAL:
```
{conteudo_atual}
```

{"DESCRIÇÃO DO BUG: " + descricao_bug if descricao_bug else "Analise o código e identifique possíveis bugs ou problemas."}

INSTRUÇÕES:
1. Analise o código cuidadosamente
2. Identifique bugs, erros ou problemas
3. Corrija mantendo funcionalidade existente
4. Retorne APENAS o código corrigido completo
5. Se não houver bugs óbvios, retorne o código original

FORMATO DE RESPOSTA:
Retorne o código corrigido completo, pronto para substituir o arquivo inteiro.

CÓDIGO CORRIGIDO:"""

        resposta_ia = perguntar_yui(prompt, None)

        if not resposta_ia or resposta_ia.get("status") != "ok":
            return False, None, "Falha ao analisar código via IA"

        dados_resposta = resposta_ia.get("data", {})
        conteudo_novo = _extrair_codigo_da_resposta(dados_resposta, conteudo_atual)

        if not conteudo_novo:
            return False, None, "Não foi possível extrair código corrigido"

        explicacao = f"🐛 Correção de bug em {os.path.basename(arquivo_abs)}\n"
        if descricao_bug:
            explicacao += f"📋 Bug descrito: {descricao_bug}\n\n"
        
        # Menciona regras relevantes se houver contexto arquitetural
        if contexto_arquitetural:
            regras_obrigatorias = []
            for linha in contexto_arquitetural.split("\n"):
                if linha.strip().startswith("- ") and "REGRAS OBRIGATÓRIAS" in contexto_arquitetural:
                    regras_obrigatorias.append(linha.strip()[2:])
            
            if regras_obrigatorias:
                explicacao += "📐 Regras do projeto aplicadas:\n"
                for regra in regras_obrigatorias[:3]:
                    explicacao += f"  • {regra}\n"
                explicacao += "\n"
        
        explicacao += "💡 Código corrigido conforme análise da IA.\n"
        explicacao += "Revise o diff abaixo para ver as correções."

        resultado_preparacao = preparar_edicao_codigo(
            arquivo_abs,
            conteudo_novo,
            f"Correção de bug: {descricao_bug or 'Análise automática'}"
        )

        if not resultado_preparacao.get("ok"):
            return False, None, resultado_preparacao.get("mensagem", "Falha ao preparar edição")

        resultado = {
            "patch": resultado_preparacao["dados"]["patch"],
            "visualizacao": resultado_preparacao["dados"]["visualizacao"],
            "explicacao": explicacao,
            "arquivo": arquivo_abs,
            "conteudo_antigo": conteudo_atual,
            "conteudo_novo": conteudo_novo
        }

        return True, resultado, None

    except Exception as e:
        return False, None, str(e)
