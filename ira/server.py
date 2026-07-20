# ira/server.py
#
# Thin shim so that `python -m ira.server` works without any sys.modules aliasing.
# All real logic lives in backend.ira.server; this module simply delegates to it.

from backend.ira.server import *          # noqa: F401, F403  – re-export public API
from backend.ira.server import main       # explicit import so -m finds __main__

if __name__ == "__main__":
    main()
