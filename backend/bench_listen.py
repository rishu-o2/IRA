"""
Voice pipeline benchmark.

Run from backend/:
    py -3 bench_listen.py

The script drives listen_for_command() + assistant.handle() for 5 phrases.
It captures every [PERF] line printed to stdout and saves the results to
bench_results.json in the same directory.
"""
from __future__ import annotations

import io
import json
import sys
import time

# ── stdout patch: intercept [PERF] lines BEFORE importing the voice module ────
_captured: list[str] = []
_real_stdout = sys.__stdout__


class _Tee(io.TextIOBase):
    """Write to real stdout AND accumulate [PERF] lines."""
    def write(self, s: str) -> int:
        if s.strip():
            _real_stdout.write(s)
            _real_stdout.flush()
        for line in s.splitlines():
            if "[PERF]" in line:
                _captured.append(line.strip())
        return len(s)

    def flush(self) -> None:
        _real_stdout.flush()


sys.stdout = _Tee()

# ── Import pipeline (stdout already patched) ──────────────────────────────────
from ira.voice import listen_for_command   # noqa: E402
from ira.assistant import IRAAssistant     # noqa: E402

assistant = IRAAssistant()

PHRASES = [
    "Hello",
    "Open Calculator",
    "Open Notepad",
    "What time is it",
    "Thank you",
]

results: list[dict] = []

for i, phrase in enumerate(PHRASES, 1):
    _captured.clear()
    _real_stdout.write(f"\n{'='*60}\n")
    _real_stdout.write(
        f"[BENCH] Request {i}/5  >>>  Say: \"{phrase}\"\n"
        f"        Press ENTER when ready to listen...\n"
    )
    _real_stdout.flush()
    input()  # pause so the user can prepare

    wall_start = time.perf_counter()

    transcript = listen_for_command()

    if transcript:
        response = assistant.handle(transcript)
        response_text = response.text
    else:
        response_text = "(no transcript)"

    wall_ms = (time.perf_counter() - wall_start) * 1000

    results.append({
        "request": i,
        "target_phrase": phrase,
        "transcript": transcript,
        "response": response_text,
        "perf_lines": list(_captured),
        "wall_ms": round(wall_ms),
    })

# ── Restore stdout and print summary ─────────────────────────────────────────
sys.stdout = _real_stdout

print("\n\n" + "=" * 60)
print("  BENCHMARK COMPLETE")
print("=" * 60)
for r in results:
    print(f"\nRequest {r['request']}: target='{r['target_phrase']}'")
    print(f"  Heard     : {r['transcript']}")
    print(f"  Response  : {r['response']}")
    print(f"  Wall clock: {r['wall_ms']} ms")
    print("  [PERF] lines:")
    for line in r["perf_lines"]:
        print(f"    {line}")

out_path = "bench_results.json"
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, ensure_ascii=False)
print(f"\n[BENCH] Full JSON results written to {out_path}")
