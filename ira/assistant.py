from __future__ import annotations

import sys

from backend.ira import assistant as _assistant

sys.modules[__name__] = _assistant
