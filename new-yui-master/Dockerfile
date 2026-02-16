# Yui - Deploy Zeabur
FROM python:3.11-slim

WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto
COPY . .

# Fail-fast: evita deploy com erro de sintaxe (ex.: worker failed to boot).
RUN python -m compileall -q /app

# Porta (Zeabur injeta PORT)
ENV PORT=8080
EXPOSE 8080

# 1 worker para 2GB RAM (cada worker duplica memória)
ENV WEB_CONCURRENCY=1

# Gunicorn direto (evita main.py)
CMD gunicorn --workers 1 --threads 2 --timeout 300 --bind 0.0.0.0:${PORT} web_server:app
