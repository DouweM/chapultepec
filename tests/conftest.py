"""Shared test fixtures/paths for pychapultepec."""

from __future__ import annotations

import sys
from pathlib import Path

# Append (not insert) the integration dir so `pychapultepec` resolves without
# the integration's own `http.py`/`const.py` shadowing stdlib modules.
_INTEGRATION = Path(__file__).resolve().parent.parent / "custom_components" / "chapultepec"
if str(_INTEGRATION) not in sys.path:
    sys.path.append(str(_INTEGRATION))
