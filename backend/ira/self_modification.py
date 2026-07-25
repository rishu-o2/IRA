"""
self_modification.py – Self-modification engine for IRA.

Extracted from IRAAssistant._apply_self_modifications.

Processes <write_file> and <patch_file> XML-style tags embedded in LLM
replies to allow the assistant to modify its own codebase at runtime.

The engine is stateless; callers supply the mutation lists so that
IRAAssistant can remain the owner of modification_history.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .virtual_world import VirtualWorld


class SelfModificationEngine:
    """Applies write-file and patch-file directives from an LLM reply."""

    def __init__(self, project_root: Path | None = None) -> None:
        # Default: two levels up from this file (backend/ira -> backend -> project root)
        self._project_root: Path = project_root or Path(__file__).resolve().parents[2]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(
        self,
        reply_text: str,
        recent_modifications: list,
        modification_history: list,
        virtual_world: "VirtualWorld | None" = None,
    ) -> list[str]:
        """Process any self-modification tags in *reply_text*.

        Appends entries to *recent_modifications* and *modification_history*
        in-place (both owned by IRAAssistant) and returns the list of
        relative paths that were successfully written or patched.
        """
        applied_files: list[str] = []

        self._apply_write_tags(
            reply_text, applied_files, recent_modifications, modification_history
        )
        self._apply_patch_tags(
            reply_text, applied_files, recent_modifications, modification_history
        )

        if applied_files and virtual_world is not None:
            virtual_world.update_state(
                "last_interaction", f"Modified {', '.join(applied_files)}"
            )
            for f in applied_files:
                kb = virtual_world.state.setdefault("knowledge_base", [])
                if f not in kb:
                    kb.append(f)

        return applied_files

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _safe_resolve(self, rel_path: str) -> Path:
        target = (self._project_root / rel_path.strip()).resolve()
        if (
            self._project_root not in target.parents
            and target != self._project_root
        ):
            raise ValueError(
                f"Path traversal detected: {rel_path} resolves outside project root."
            )
        return target

    def _apply_write_tags(
        self,
        reply_text: str,
        applied_files: list,
        recent_modifications: list,
        modification_history: list,
    ) -> None:
        pattern = r'<write_file\s+path="([^"]+)"\s*>(.*?)</write_file>'
        for match in re.finditer(pattern, reply_text, re.DOTALL):
            rel_path, content = match.group(1), match.group(2)
            try:
                target_path = self._safe_resolve(rel_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                applied_files.append(rel_path)
                entry = {"path": rel_path, "type": "write", "content": content}
                recent_modifications.append(entry)
                modification_history.append(entry)
            except Exception as exc:
                print(
                    f'Error executing self-modification <write_file path="{rel_path}">: {exc}'
                )

    def _apply_patch_tags(
        self,
        reply_text: str,
        applied_files: list,
        recent_modifications: list,
        modification_history: list,
    ) -> None:
        pattern = r'<patch_file\s+path="([^"]+)"\s*>(.*?)</patch_file>'
        for match in re.finditer(pattern, reply_text, re.DOTALL):
            rel_path, patch_content = match.group(1), match.group(2)
            try:
                target_path = self._safe_resolve(rel_path)
                if not target_path.exists():
                    raise FileNotFoundError(
                        f"Cannot patch non-existent file: {target_path}"
                    )

                file_content = target_path.read_text(encoding="utf-8")
                blocks = re.findall(
                    r"<<<<(.*?)====(.*?)>>>>", patch_content, re.DOTALL
                )
                modified = False
                logged_blocks: list[dict] = []
                for search, replace in blocks:
                    search_clean = search.strip("\r\n")
                    replace_clean = replace.strip("\r\n")
                    if search_clean in file_content:
                        file_content = file_content.replace(search_clean, replace_clean, 1)
                        modified = True
                        logged_blocks.append(
                            {"search": search_clean, "replace": replace_clean}
                        )
                    else:
                        print(
                            f"Patch search block not found in {rel_path}:\n{search_clean}"
                        )

                if modified:
                    target_path.write_text(file_content, encoding="utf-8")
                    applied_files.append(rel_path)
                    entry = {"path": rel_path, "type": "patch", "blocks": logged_blocks}
                    recent_modifications.append(entry)
                    modification_history.append(entry)
            except Exception as exc:
                print(
                    f'Error executing self-modification <patch_file path="{rel_path}">: {exc}'
                )
