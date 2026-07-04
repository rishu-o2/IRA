import sys
import pathlib
# Ensure the project root (two levels up) is on sys.path for imports like 'ira'
project_root = pathlib.Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
