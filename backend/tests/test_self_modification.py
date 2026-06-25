from __future__ import annotations

import os
import textwrap
from pathlib import Path
import pytest
from ira.assistant import IRAAssistant


@pytest.fixture
def temp_test_file() -> Path:
    # Set up a temp file inside backend/ for testing
    project_root = Path(__file__).resolve().parents[2]
    temp_path = project_root / "backend" / "temp_self_mod_test.txt"
    if temp_path.exists():
        temp_path.unlink()
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


def test_write_file_self_modification(temp_test_file: Path) -> None:
    assistant = IRAAssistant()
    rel_path = "backend/temp_self_mod_test.txt"

    reply_text = textwrap.dedent(f"""
    Sure, I'll create that file for you.
    <write_file path="{rel_path}">
    hello from self modification!
    line 2
    </write_file>
    Let me know if you need changes.
    """)

    applied = assistant._apply_self_modifications(reply_text)
    
    assert rel_path in applied
    assert temp_test_file.exists()
    assert temp_test_file.read_text(encoding="utf-8").strip() == "hello from self modification!\nline 2"


def test_patch_file_self_modification(temp_test_file: Path) -> None:
    temp_test_file.write_text("line A\nline B\nline C", encoding="utf-8")
    
    assistant = IRAAssistant()
    rel_path = "backend/temp_self_mod_test.txt"

    reply_text = textwrap.dedent(f"""
    Updating the file.
    <patch_file path="{rel_path}">
    <<<<
    line B
    ====
    line B modified!
    >>>>
    </patch_file>
    Done!
    """)

    applied = assistant._apply_self_modifications(reply_text)
    
    assert rel_path in applied
    content = temp_test_file.read_text(encoding="utf-8")
    assert "line B modified!" in content
    assert "line A" in content
    assert "line C" in content


def test_path_traversal_protection() -> None:
    assistant = IRAAssistant()
    
    # Try to write to a path outside the workspace
    reply_text = textwrap.dedent("""
    Writing malicious path.
    <write_file path="../../outside_workspace.txt">
    malicious content
    </write_file>
    """)
    
    # Executing the self-modification should catch the traversal and log it without writing
    # (since the exception is caught and printed)
    applied = assistant._apply_self_modifications(reply_text)
    assert not applied
