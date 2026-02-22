"""
Yui Tools — Implementação das ferramentas técnicas.
- analisar_codigo: vulnerabilidades, más práticas, arquitetura
- sugerir_arquitetura: estrutura de pastas e responsabilidades
- calcular_custo_estimado: estimativa de custo em tokens
- resumir_contexto: resumo técnico para memória
"""

from typing import Any, Dict


def analisar_codigo(codigo: str) -> Dict[str, Any]:
    """
    Detecta vulnerabilidades, más práticas, problemas de arquitetura.
    Retorna: {ok, relatorio, vulnerabilidades, sugestoes}
    """
    if not codigo or not isinstance(codigo, str):
        return {"ok": False, "erro": "Código vazio ou inválido."}

    codigo = codigo.strip()
    if codigo.startswith("```"):
        lines = codigo.split("\n")
        if lines[-1].strip() == "```":
            codigo = "\n".join(lines[1:-1])
        else:
            codigo = "\n".join(lines[1:])

    try:
        from yui_ai.tools.code_analyzer import analisar_codigo as _analisar
        result = _analisar(codigo, {"content": codigo, "filename": "codigo.py"})
        if result.get("ok"):
            return {
                "ok": True,
                "relatorio": result.get("texto", ""),
                "vulnerabilidades": _extrair_vulnerabilidades(result.get("relatorio")),
                "sugestoes": result.get("texto", ""),
            }
        return {
            "ok": False,
            "erro": result.get("erro", "Falha na análise."),
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def _extrair_vulnerabilidades(relatorio: Any) -> list:
    if not relatorio:
        return []
    if isinstance(relatorio, dict):
        problemas = relatorio.get("problemas", []) or relatorio.get("riscos", [])
        return [str(p.get("mensagem", p)) for p in problemas] if problemas else []
    return []


def sugerir_arquitetura(tipo_projeto: str) -> Dict[str, Any]:
    """
    Retorna estrutura ideal de pastas e responsabilidades.
    tipo_projeto: web, api, mobile, fullstack, microsaas, etc.
    """
    tipo = (tipo_projeto or "").strip().lower()
    if not tipo:
        return {"ok": False, "erro": "Informe o tipo de projeto."}

    templates: Dict[str, Dict[str, Any]] = {
        "web": {
            "estrutura": "src/\n  components/\n  pages/\n  styles/\n  utils/\npublic/\nstatic/\npackage.json",
            "responsabilidades": "components: UI reutilizáveis | pages: rotas/views | styles: CSS/SCSS",
        },
        "api": {
            "estrutura": "src/\n  routes/\n  controllers/\n  models/\n  services/\n  middleware/\nconfig/\ntests/",
            "responsabilidades": "routes: endpoints | controllers: lógica HTTP | models: dados | services: regras de negócio",
        },
        "mobile": {
            "estrutura": "src/\n  screens/\n  components/\n  navigation/\n  hooks/\n  services/\nassets/\n",
            "responsabilidades": "screens: telas | components: UI | navigation: rotas | hooks: lógica reutilizável",
        },
        "fullstack": {
            "estrutura": "backend/\n  api/\n  models/\n  services/\nfrontend/\n  src/\n    components/\n    pages/\nshared/\n  types/\n  utils/",
            "responsabilidades": "backend: API e dados | frontend: UI | shared: tipos e utils compartilhados",
        },
        "microsaas": {
            "estrutura": "app/\n  api/\n  auth/\n  dashboard/\n  pages/\nlib/\n  db/\n  auth/\n  billing/\ncomponents/\nprisma/",
            "responsabilidades": "app: Next.js app router | lib: db, auth, billing | components: UI",
        },
        "python": {
            "estrutura": "src/\n  __init__.py\n  main.py\n  app/\n  routes/\n  models/\n  services/\nconfig/\ntests/\nrequirements.txt",
            "responsabilidades": "app: aplicação | routes: endpoints | models: ORM | services: lógica",
        },
    }

    for key, val in templates.items():
        if key in tipo or tipo in key:
            return {
                "ok": True,
                "tipo": tipo,
                "estrutura": val["estrutura"],
                "responsabilidades": val["responsabilidades"],
            }

    return {
        "ok": True,
        "tipo": tipo,
        "estrutura": "src/\n  components/\n  services/\n  utils/\nconfig/\ntests/",
        "responsabilidades": "Estrutura genérica. Especifique: web, api, mobile, fullstack ou microsaas.",
    }


def calcular_custo_estimado(tokens_entrada: int, tokens_saida: int) -> Dict[str, Any]:
    """
    Retorna estimativa de custo em USD e BRL.
    Baseado em gpt-4o-mini: input $0.15/1M, output $0.60/1M
    """
    try:
        from core.usage_tracker import (
            PRICE_INPUT_PER_1M,
            PRICE_OUTPUT_PER_1M,
            BRL_PER_USD,
        )
    except ImportError:
        PRICE_INPUT_PER_1M = 0.15
        PRICE_OUTPUT_PER_1M = 0.60
        BRL_PER_USD = 5.0

    inp = max(0, int(tokens_entrada))
    out = max(0, int(tokens_saida))
    usd = (inp * PRICE_INPUT_PER_1M / 1_000_000) + (out * PRICE_OUTPUT_PER_1M / 1_000_000)
    brl = round(usd * BRL_PER_USD, 4)
    return {
        "ok": True,
        "tokens_entrada": inp,
        "tokens_saida": out,
        "custo_usd": round(usd, 6),
        "custo_brl": brl,
    }


def resumir_contexto(conversa: str) -> Dict[str, Any]:
    """
    Retorna resumo técnico curto para memória.
    Usado quando histórico > 10 mensagens.
    """
    if not conversa or not isinstance(conversa, str):
        return {"ok": False, "erro": "Conversa vazia."}

    conversa = conversa.strip()
    if len(conversa) < 50:
        return {"ok": True, "resumo": conversa[:200]}

    try:
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        if not client.api_key:
            return {"ok": True, "resumo": conversa[:2000] + "..." if len(conversa) > 2000 else conversa}

        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Resuma em 2-4 frases técnicas o essencial desta conversa. Use português."},
                {"role": "user", "content": conversa[:8000]},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        resumo = ""
        if r.choices and len(r.choices) > 0:
            resumo = (r.choices[0].message.content or "").strip()
        return {"ok": True, "resumo": resumo or conversa[:500]}
    except Exception:
        return {"ok": True, "resumo": conversa[:1500] + "..." if len(conversa) > 1500 else conversa}


def executar_tool(nome: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatcher: executa a tool pelo nome."""
    if nome == "analisar_codigo":
        return analisar_codigo(args.get("codigo", "") or "")
    if nome == "sugerir_arquitetura":
        return sugerir_arquitetura(args.get("tipo_projeto", "") or "")
    if nome == "calcular_custo_estimado":
        return calcular_custo_estimado(
            int(args.get("tokens_entrada", 0) or 0),
            int(args.get("tokens_saida", 0) or 0),
        )
    if nome == "resumir_contexto":
        return resumir_contexto(args.get("conversa", "") or "")
    return {"ok": False, "erro": f"Tool desconhecida: {nome}"}
