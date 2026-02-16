"""
Pytest configuration — garante que a raiz do projeto está no sys.path.
Execute os testes sempre da raiz: python -m pytest tests/ -v
"""
import sys
from pathlib import Path

# Raiz do projeto (pasta que contém web_server.py, cli.py)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
