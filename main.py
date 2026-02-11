#!/usr/bin/env python3
"""
Ponto de entrada para Zeabur (detecta python main.py).
Redireciona para gunicorn rodando web_server:app.
"""
import os
import sys

# Zeabur executa python main.py por padrão
port = os.environ.get("PORT", "5000")
argv = [
    "--workers", "1",
    "--threads", "2",
    "--timeout", "300",
    "--bind", f"0.0.0.0:{port}",
    "web_server:app",
]
os.execv(sys.executable, [sys.executable, "-m", "gunicorn"] + argv)
