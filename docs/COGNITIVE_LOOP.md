# Cognitive Loop — Metabolismo da Yui

Executor → Observer → Self-Critic → Memory Update

## Fluxo

```
Input → Planner → Executor → Observer → Self-Critic → Memory Update
```

## Módulos

### 1. Observer (`core/cognitive/observer.py`)

Registra por turno:
- tempo de execução
- tokens usados (prompt + completion)
- tools executadas
- arquivos alterados
- erros detectados
- modo (answer | tool | tools | skill)

### 2. Self-Critic (`core/cognitive/self_critic.py`)

Avalia sem gerar código:
- a ação foi eficiente?
- gerou erro?
- abriu loops desnecessários?
- aumentou RAM?

Retorna `CritiqueResult` com `efficient`, `had_error`, `loop_detected`, `ram_impact`, `score`, `feedback`.

### 3. Action Scoring (`core/cognitive/action_scoring.py`)

Micro-RL sem treinar modelo:

| Score | Situação |
|-------|----------|
| +3 | resolveu erro |
| +2 | reduziu código / criou arquivo útil |
| +1 | ação concluída com sucesso |
| 0 | neutro |
| -1 | criou warning / execução lenta |
| -2 | ação redundante / loop |
| -3 | causou crash / erro grave |

Após algumas execuções, a IA tende a preferir caminhos melhores (via `set_confidence`).

## Integração

- **agent_controller**: após gerar `reply`, chama `observe_turn` e `criticize`
- **set_confidence**: ajustado pelo Self-Critic (eficiência ↑ → confiança ↑)
- **API**: `GET /api/system/cognitive` retorna status para o painel

## Observability UI

Painel **Cognitive Status** na sidebar:
- Planner Confidence: 0–100%
- Last Action Score: A+ a F
- RAM Impact: low | medium | high

Atualiza a cada 10s e após cada resposta.
