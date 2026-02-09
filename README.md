# Yui — Analisador técnico de projetos

Ferramenta **profissional de análise de projetos de código** via CLI. Somente leitura: **nunca altera** o código do projeto analisado.

## Requisitos

- Python 3.11+

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso via CLI

### Analisar um projeto

```bash
yui analyze <caminho_do_projeto>
```

Exemplos:

```bash
# Analisar o diretório atual
python cli.py analyze .

# Analisar outro projeto
python cli.py analyze ./meu-projeto

# Via módulo
python -m yui_ai analyze ./meu-projeto
```

### O que a análise faz

- **Escaneia** a estrutura de pastas e arquivos
- **Mapeia** arquivos Python e imports (AST)
- **Detecta** responsabilidades e padrões arquiteturais
- **Identifica** dependências circulares
- **Avalia** pontos fortes, fracos e riscos técnicos
- **Gera** relatório técnico no terminal (roadmap de melhorias)

Nenhum arquivo do projeto analisado é modificado.

## Estrutura do analisador

```
yui_ai/
  analyzer/
    project_scanner.py   # Estrutura de pastas e listagem de .py
    dependency_mapper.py # Grafo de imports (AST), ciclos
    architecture_analyzer.py # Responsabilidades e camadas
    risk_detector.py     # Pontos fortes/fracos, riscos
    report_builder.py    # Orquestração e relatório final
cli.py                  # Entrypoint CLI (yui analyze)
```

## Desenvolvimento

```bash
# Rodar análise no próprio projeto Yui
python cli.py analyze .
```

## Licença

Uso interno / projeto pessoal.
