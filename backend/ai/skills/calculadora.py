# Skill de exemplo: operações simples.
# A YUI pode usar esta skill quando o usuário pedir contas.

def run(dados):
    a = dados.get("a", 0)
    b = dados.get("b", 0)
    op = (dados.get("op") or "soma").strip().lower()
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return {"erro": "Valores 'a' e 'b' devem ser números."}
    if op in ("soma", "+", "add"):
        return {"resultado": a + b, "operacao": "soma"}
    if op in ("subtração", "subtracao", "-", "sub"):
        return {"resultado": a - b, "operacao": "subtracao"}
    if op in ("multiplicação", "multiplicacao", "*", "mul"):
        return {"resultado": a * b, "operacao": "multiplicacao"}
    if op in ("divisão", "divisao", "/", "div"):
        if b == 0:
            return {"erro": "Divisão por zero."}
        return {"resultado": a / b, "operacao": "divisao"}
    return {"resultado": a + b, "operacao": "soma (default)"}
