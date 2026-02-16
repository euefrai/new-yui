"""
Fase 5: Planejamento e Análise de Impacto.

REGRAS OBRIGATÓRIAS:
1. Nenhuma edição de código pode começar sem um plano aprovado pelo usuário.
2. O plano deve incluir: objetivo, arquivos/funções afetadas, impacto, riscos,
   relação com regras da memória arquitetural.
3. O plano é exibido de forma clara e estruturada antes de qualquer geração de código.
"""

import os
import json
from typing import Dict, List, Optional, Tuple


def gerar_plano_edicao(
    arquivo: str,
    instrucao: str,
    contexto_adicional: str = "",
    acao: str = "gerar_codigo_refatorado",
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Gera um plano explícito de edição ANTES de qualquer alteração de código.

    Retorna: (sucesso, plano, mensagem_erro)
    plano = {
        "objetivo": str,
        "arquivos_funcoes": str ou list,
        "impacto_tecnico": str,
        "riscos": str,
        "relacao_regras": str,
        "texto_formatado": str  # para exibição clara ao usuário
    }
    """
    arquivo_abs = os.path.abspath(arquivo)

    if not os.path.exists(arquivo_abs):
        return False, None, f"Arquivo não encontrado: {arquivo_abs}"

    if os.path.isdir(arquivo_abs):
        return False, None, f"Caminho é uma pasta, não um arquivo: {arquivo_abs}"

    try:
        # 1. Contexto arquitetural (regras, padrões, restrições)
        contexto_arquitetural = ""
        try:
            from yui_ai.architecture.memory_store import ArchitectureMemory
            memory = ArchitectureMemory()
            contexto_arquitetural = memory.montar_contexto_arquitetural(
                arquivo_abs, instrucao
            )
        except Exception:
            pass

        # 2. Conteúdo atual (resumo ou primeiras linhas para contexto)
        try:
            with open(arquivo_abs, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()
            linhas = conteudo.split("\n")
            amostra = "\n".join(linhas[:50]) if len(linhas) > 50 else conteudo
            if len(linhas) > 50:
                amostra += "\n..."
        except Exception:
            amostra = "(não foi possível ler o arquivo)"

        # 3. Tenta gerar plano via IA
        plano_dict = _gerar_plano_via_ia(
            arquivo_abs,
            instrucao,
            contexto_adicional,
            contexto_arquitetural,
            amostra,
            acao,
        )

        if plano_dict is None:
            # Fallback: plano mínimo sem IA
            plano_dict = _plano_minimo(arquivo_abs, instrucao, contexto_arquitetural)

        # 4. Garante texto formatado para exibição
        plano_dict["texto_formatado"] = _formatar_plano_para_exibicao(plano_dict)
        return True, plano_dict, None

    except Exception as e:
        return False, None, str(e)


def _gerar_plano_via_ia(
    arquivo: str,
    instrucao: str,
    contexto_adicional: str,
    contexto_arquitetural: str,
    amostra_codigo: str,
    acao: str,
) -> Optional[Dict]:
    """Chama a IA para gerar o plano. Retorna None se IA indisponível ou falha."""
    try:
        from yui_ai.core.ai_engine import perguntar_yui
    except Exception:
        return None

    nome_arquivo = os.path.basename(arquivo)
    prompt = _montar_prompt_plano(
        nome_arquivo,
        instrucao,
        contexto_adicional,
        contexto_arquitetural,
        amostra_codigo,
        acao,
    )

    resposta = perguntar_yui(prompt, None)
    if not resposta or resposta.get("status") != "ok":
        return None

    dados = resposta.get("data", {})
    # Tenta extrair plano estruturado (IA pode retornar JSON ou texto)
    return _extrair_plano_da_resposta(dados, arquivo, instrucao, contexto_arquitetural)


def _montar_prompt_plano(
    nome_arquivo: str,
    instrucao: str,
    contexto_adicional: str,
    contexto_arquitetural: str,
    amostra_codigo: str,
    acao: str,
) -> str:
    """Monta prompt para a IA gerar APENAS o plano (sem código)."""
    return f"""Você é um assistente de planejamento de mudanças em código.

TAREFA: Gerar um PLANO de edição (NÃO gere código ainda). Apenas descreva o que será feito.

ARQUIVO: {nome_arquivo}
INSTRUÇÃO DO USUÁRIO: {instrucao}
{contexto_adicional}

CONTEXTO ARQUITETURAL DO PROJETO (respeitar nas mudanças):
{contexto_arquitetural or "(nenhuma regra registrada)"}

AMOSTRA DO CÓDIGO ATUAL (início do arquivo):
```
{amostra_codigo[:3000]}
```

Responda em JSON com exatamente estes campos (texto em português):
- "objetivo": resumo claro do objetivo da mudança
- "arquivos_funcoes": descrição de quais arquivos e funções/classes serão afetados
- "impacto_tecnico": impacto técnico esperado (comportamento, dependências, testes)
- "riscos": riscos potenciais (quebras, efeitos colaterais)
- "relacao_regras": como a mudança se relaciona com as regras/padrões do projeto acima

Retorne APENAS o JSON, sem markdown e sem texto antes/depois."""


def _extrair_plano_da_resposta(
    dados: dict,
    arquivo: str,
    instrucao: str,
    contexto_arquitetural: str,
) -> Dict:
    """Extrai plano da resposta da IA (JSON ou fallback em campos fixos)."""
    texto = dados.get("resposta", "")
    if not texto:
        return _plano_minimo(arquivo, instrucao, contexto_arquitetural)

    # Tenta parsear JSON
    texto_limpo = texto.strip()
    if texto_limpo.startswith("```"):
        partes = texto_limpo.split("```")
        for p in partes:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                try:
                    obj = json.loads(p)
                    return {
                        "objetivo": obj.get("objetivo", ""),
                        "arquivos_funcoes": obj.get("arquivos_funcoes", ""),
                        "impacto_tecnico": obj.get("impacto_tecnico", ""),
                        "riscos": obj.get("riscos", ""),
                        "relacao_regras": obj.get("relacao_regras", ""),
                    }
                except json.JSONDecodeError:
                    pass
    if texto_limpo.startswith("{"):
        try:
            obj = json.loads(texto_limpo)
            return {
                "objetivo": obj.get("objetivo", ""),
                "arquivos_funcoes": obj.get("arquivos_funcoes", ""),
                "impacto_tecnico": obj.get("impacto_tecnico", ""),
                "riscos": obj.get("riscos", ""),
                "relacao_regras": obj.get("relacao_regras", ""),
            }
        except json.JSONDecodeError:
            pass

    # Fallback: usa o texto como objetivo e preenche o resto
    return _plano_minimo(arquivo, instrucao, contexto_arquitetural, objetivo_extra=texto[:500])


def _plano_minimo(
    arquivo: str,
    instrucao: str,
    contexto_arquitetural: str,
    objetivo_extra: str = "",
) -> Dict:
    """Plano mínimo quando IA não está disponível ou não retornou JSON válido."""
    nome = os.path.basename(arquivo)
    return {
        "objetivo": objetivo_extra or f"Alteração solicitada: {instrucao}",
        "arquivos_funcoes": f"Arquivo principal: {nome} (funções/classes a definir na geração)",
        "impacto_tecnico": "Será avaliado na geração do diff. Validação (sintaxe/testes/linter) será executada após aplicar.",
        "riscos": "Riscos serão mitigados pela confirmação do diff antes de aplicar e pela validação pós-edição.",
        "relacao_regras": f"Regras do projeto serão respeitadas na geração do código.\n{contexto_arquitetural[:500]}" if contexto_arquitetural else "Nenhuma regra arquitetural registrada no momento.",
    }


def _formatar_plano_para_exibicao(plano: Dict) -> str:
    """Gera texto estruturado para exibir o plano ao usuário."""
    linhas = [
        "",
        "=" * 60,
        "  PLANO DE EDIÇÃO (Fase 5 – Planejamento e Análise de Impacto)",
        "=" * 60,
        "",
        "► OBJETIVO",
        "-" * 40,
        (plano.get("objetivo") or "(não informado)").strip(),
        "",
        "► ARQUIVOS / FUNÇÕES AFETADAS",
        "-" * 40,
        _str(plano.get("arquivos_funcoes")),
        "",
        "► IMPACTO TÉCNICO ESPERADO",
        "-" * 40,
        _str(plano.get("impacto_tecnico")),
        "",
        "► RISCOS POTENCIAIS",
        "-" * 40,
        _str(plano.get("riscos")),
        "",
        "► RELAÇÃO COM REGRAS DA MEMÓRIA ARQUITETURAL",
        "-" * 40,
        _str(plano.get("relacao_regras")),
        "",
        "=" * 60,
    ]
    return "\n".join(linhas)


def _str(val) -> str:
    """Converte valor para string (list/dict vira texto)."""
    if val is None:
        return "(não informado)"
    if isinstance(val, list):
        return "\n".join(str(x) for x in val)
    if isinstance(val, dict):
        return "\n".join(f"- {k}: {v}" for k, v in val.items())
    return str(val).strip() or "(não informado)"
