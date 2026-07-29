import os

_DEBUG = os.environ.get("IRA_DEBUG") == "1" or os.environ.get("PIPELINE_DEBUG") == "1"

def pipeline_log(layer: str, message: str) -> None:
    if _DEBUG:
        print(f"[PIPELINE] [{layer}] {message}")
