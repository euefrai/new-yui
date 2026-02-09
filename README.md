# Yui — Assistente de código e analisador de projetos

Assistente de código autônoma com **chat web** (estilo WhatsApp/Instagram) e **análise de projetos** via CLI. Memória persistente, resposta contextual e geração de código em várias linguagens.

## Requisitos

- Python 3.11+

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Chat web (local)

```bash
python web_server.py
```

Acesse: **http://127.0.0.1:5000**

Configure `OPENAI_API_KEY` no arquivo `.env` (copie de `.env.example`) para usar a IA.

## Deploy no Render

1. Faça push deste repositório para o GitHub.
2. Acesse [render.com](https://render.com) e crie uma conta (ou use “Sign in with GitHub”).
3. **New** → **Blueprint** e conecte o repositório **euefrai/new-yui** (ou o seu fork).
4. O `render.yaml` já define o serviço. Confirme:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn --bind 0.0.0.0:$PORT web_server:app`
5. Em **Environment** adicione:
   - `OPENAI_API_KEY` = sua chave da OpenAI (obrigatório para o chat com IA).
6. Clique em **Apply** e aguarde o deploy.

O Render vai gerar uma URL como `https://yui-xxxx.onrender.com`. Use essa URL no navegador para o chat. Em plano gratuito o serviço pode “dormir” após inatividade; a primeira requisição pode demorar alguns segundos.

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

## Estrutura do projeto

```
yui_ai/          # Core da assistente (memória, IA, analisador)
web/             # Interface do chat (HTML, CSS, JS)
web_server.py    # App Flask (chat + API)
render.yaml      # Configuração de deploy no Render
cli.py           # CLI (yui analyze)
```

## Licença

Uso interno / projeto pessoal.
