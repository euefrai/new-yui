"""
Entrypoint quando executado como python -m yui_ai.

Uso:
  python -m yui_ai analyze ./projeto
  python -m yui_ai analyze .
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if __name__ == "__main__":
    from cli import main
    sys.exit(main())
