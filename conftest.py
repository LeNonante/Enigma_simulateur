"""Rend le dépôt importable quel que soit l'outil lancé (« pytest » ou « python -m pytest »).

Les modules (enigma.py, web.py…) sont à la racine du dépôt et les tests dans
tests/ : sans cette ligne, seul « python -m pytest » les trouvait.
"""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
