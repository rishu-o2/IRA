from __future__ import annotations

import time
from datetime import datetime
from dataclasses import dataclass

from .actions import (
    ActionError,
    lock_screen,
    mute_system,
    open_app,
    open_known_folder,
    open_path,
    open_website,
    play_youtube_search,
    search_web,
    shutdown_system,
    sleep_system,
    volume_up,
    volume_down,
    set_brightness,
    get_battery_status,
    get_system_stats,
)
from .conversation import ConversationError, GeminiConversation


@dataclass(frozen=True)
class AssistantResponse:
    text: str
    handled: bool = True


class IRAAssistant:
    def __init__(self, conversation: GeminiConversation | None = None) -> None:
        self.conversation = conversation or GeminiConversation()
        from .virtual_world import VirtualWorld
        self.virtual_world = VirtualWorld()
        self.recent_modifications = []
        self.modification_history = []
        self._llm_time: float = 0.0  # seconds; set by _handle_internal when LLM is called

    # ------------------------------------------------------------------
    # Public entry point — measures and logs per-stage performance
    # ------------------------------------------------------------------
    def handle(self, message: str) -> AssistantResponse:
        """Profiling wrapper: delegates to _handle_internal and prints [PERF] logs."""
        self._llm_time = 0.0
        t_start = time.perf_counter()
        response = self._handle_internal(message)
        t_end   = time.perf_counter()

        total_ms  = (t_end - t_start) * 1000
        llm_ms    = self._llm_time * 1000
        intent_ms = total_ms - llm_ms

        print(f"[PERF] Command processing: {intent_ms:.0f} ms")
        print(f"[PERF] Gemini response generation: {llm_ms:.0f} ms")
        return response

    def _handle_internal(self, message: str) -> AssistantResponse:
        command = self._normalize_command(message)
        lowered = command.lower()
        self.recent_modifications = []

        if not command:
            return AssistantResponse("I'm here. Tell me what you want to do.", handled=False)

        try:
            if lowered in {"commands"}:
                return AssistantResponse(self._help_text())

            if any(phrase in lowered for phrase in {
                "what did you update",
                "what did you change",
                "recent modifications",
                "recent updates",
                "show modifications",
                "show updates",
                "what changes did you make",
                "what have you updated",
                "show me what you updated",
                "show me what you are updating",
                "show me what you change",
                "show me the changes",
                "show me the code changes",
                "show me the code you changed",
                "where did you update",
                "where are you updating",
                "where did you change",
                "show me where the program is going to change",
                "show me where you are changing",
            }):
                if not self.modification_history:
                    return AssistantResponse("I have not made any modifications to my program files in this session.")
                
                lines = ["In this session, I have modified the following files:"]
                for idx, mod in enumerate(self.modification_history, 1):
                    lines.append(f"\n{idx}. `{mod['path']}` ({mod['type']} modification):")
                    if mod["type"] == "patch" and "blocks" in mod:
                        for b_idx, block in enumerate(mod["blocks"], 1):
                            lines.append(f"   Block {b_idx}:")
                            lines.append("   ```diff")
                            for line in block["search"].splitlines():
                                lines.append(f"   - {line}")
                            for line in block["replace"].splitlines():
                                lines.append(f"   + {line}")
                            lines.append("   ```")
                    elif mod["type"] == "write" and "content" in mod:
                        lines.append("   ```python")
                        content_lines = mod["content"].splitlines()
                        if len(content_lines) > 15:
                            lines.extend([f"   {l}" for l in content_lines[:15]])
                            lines.append("   ... (truncated)")
                        else:
                            lines.extend([f"   {l}" for l in content_lines])
                        lines.append("   ```")
                return AssistantResponse("\n".join(lines))

            if lowered in {"time", "what time is it", "tell me the time", "current time"}:
                return AssistantResponse(f"It is {datetime.now().strftime('%I:%M %p').lstrip('0')}.")

            if lowered in {
                "date",
                "what date is it",
                "what is today's date",
                "today's date",
                "open ira",
                "wake ira",
                "wake up ira",
                "activate ira",
                "ira",
                "open my laptop",
                "wake my laptop",
                "wake laptop",
                "open laptop",
                "activate laptop",
                "activate my laptop",
            }:
                return AssistantResponse("Hello sir. I am awake and ready.")

            if lowered.startswith(("lock screen", "lock my screen", "lock computer", "lock pc", "lock the screen")):
                return AssistantResponse(lock_screen())

            if lowered.startswith(("shut down", "shutdown", "turn off", "power off", "shut down the computer", "shutdown the computer", "turn off the computer", "power off the computer")):
                return AssistantResponse(shutdown_system())

            if lowered.startswith(("sleep", "go to sleep", "put the computer to sleep", "hibernate", "go to hibernate", "enter sleep mode", "enter hibernate mode")):
                return AssistantResponse(sleep_system())

            if lowered.startswith(("mute", "mute the volume", "silence", "turn volume off", "turn off volume", "volume mute")):
                return AssistantResponse(mute_system())

            if lowered.startswith(("unmute", "unmute the volume", "turn volume on", "turn on volume")):
                return AssistantResponse(mute_system())

            if lowered.startswith(("volume up", "increase volume", "louder", "make it louder")):
                return AssistantResponse(volume_up())

            if lowered.startswith(("volume down", "decrease volume", "quieter", "make it quieter")):
                return AssistantResponse(volume_down())

            if "brightness" in lowered:
                import re
                match = re.search(r"(\d+)", lowered)
                if match:
                    level = int(match.group(1))
                    return AssistantResponse(set_brightness(level))
                if "up" in lowered or "increase" in lowered or "brighter" in lowered:
                    return AssistantResponse(set_brightness(80))
                if "down" in lowered or "decrease" in lowered or "dimmer" in lowered:
                    return AssistantResponse(set_brightness(30))

            if lowered.startswith(("battery", "check battery", "battery status", "how is the battery")):
                return AssistantResponse(get_battery_status())

            if lowered.startswith(("system stats", "check system stats", "resource usage", "cpu usage", "performance stats")):
                return AssistantResponse(get_system_stats())

            if lowered.startswith("change mood to ") or lowered.startswith("change your mood to "):
                mood = command.split("to ", 1)[1].strip()
                return AssistantResponse(self.virtual_world.update_state("mood", mood))

            if lowered.startswith("add knowledge ") or lowered.startswith("add to knowledge base "):
                kb_item = command.split("knowledge ", 1)[1].strip()
                if kb_item not in self.virtual_world.state["knowledge_base"]:
                    self.virtual_world.state["knowledge_base"].append(kb_item)
                return AssistantResponse(f"Added {kb_item} to knowledge base.")

            if lowered in {"virtual world status", "virtual status", "show virtual world"}:
                status_dict = self.virtual_world.get_status()
                return AssistantResponse(
                    f"Virtual World Status - Mood: {status_dict['mood']}, "
                    f"Knowledge Base: {', '.join(status_dict['knowledge_base'])}, "
                    f"Last Interaction: {status_dict['last_interaction']}"
                )

            if lowered.startswith(("call ", "make a call to ")):
                try:
                    return AssistantResponse(open_app("skype"))
                except ActionError as exc:
                    return AssistantResponse(str(exc), handled=False)

            if lowered.startswith(("launch ", "start ")):
                app_name = command.split(" ", 1)[1].strip()
                return AssistantResponse(open_app(app_name))

            if lowered.startswith(("open application ", "open app ", "open program ")):
                app_name = command.split(" ", 2)[2].strip()
                return AssistantResponse(open_app(app_name))

            if lowered.startswith("go to "):
                target = command[len("go to ") :].strip()
                return AssistantResponse(open_website(target))

            if lowered.startswith("visit "):
                target = command[len("visit ") :].strip()
                return AssistantResponse(open_website(target))

            if lowered.startswith("open folder "):
                target = command[len("open folder ") :].strip()
                if self._is_known_folder(target):
                    return AssistantResponse(open_known_folder(target))
                return AssistantResponse(open_path(target))

            if lowered.startswith("open file "):
                target = command[len("open file ") :].strip()
                return AssistantResponse(open_path(target))

            if lowered.startswith("open website "):
                target = command[len("open website ") :].strip()
                return AssistantResponse(open_website(target))

            if lowered.startswith("open youtube"):
                return AssistantResponse(open_website("youtube.com"))

            if lowered.startswith("open google"):
                return AssistantResponse(open_website("google.com"))

            if lowered.startswith("open downloads"):
                return AssistantResponse(open_known_folder("downloads"))

            if lowered.startswith("open documents"):
                return AssistantResponse(open_known_folder("documents"))

            if lowered.startswith("open desktop"):
                return AssistantResponse(open_known_folder("desktop"))

            if lowered.startswith("open pictures") or lowered.startswith("open photos"):
                return AssistantResponse(open_known_folder("pictures"))

            if lowered.startswith("search google for "):
                query = command[len("search google for ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("search for "):
                query = command[len("search for ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("google "):
                query = command[len("google ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("find "):
                query = command[len("find ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("open "):
                target = command[len("open ") :].strip()
                if self._looks_like_website(target):
                    return AssistantResponse(open_website(target))
                if self._is_known_folder(target):
                    return AssistantResponse(open_known_folder(target))
                return AssistantResponse(open_app(target))

            if lowered.startswith("play "):
                query = command[len("play ") :].strip()
                if query.lower().endswith(" on youtube"):
                    query = query[: -len(" on youtube")].strip()
                return AssistantResponse(play_youtube_search(query))

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        if self._looks_sensitive_or_unsupported(lowered):
            return AssistantResponse(
                "I cannot complete that action yet. I can talk, open apps and websites, search Google, play YouTube results, and open files or folders.",
                handled=False,
            )

        try:
            t_llm_start = time.perf_counter()
            reply_text  = self.conversation.reply(command)
            self._llm_time = time.perf_counter() - t_llm_start
            applied_mods = self._apply_self_modifications(reply_text)
            if applied_mods:
                reply_text += f"\n\n[System note: Applied changes to {', '.join(applied_mods)}]"
            return AssistantResponse(reply_text)
        except ConversationError as exc:
            return AssistantResponse(str(exc), handled=False)

    def _apply_self_modifications(self, reply_text: str) -> list[str]:
        import re
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[2]

        def safe_resolve_path(rel_path: str) -> Path:
            target = (project_root / rel_path.strip()).resolve()
            if project_root not in target.parents and target != project_root:
                raise ValueError(f"Path traversal detected: {rel_path} resolves outside project root.")
            return target

        applied_files: list[str] = []

        # Parse <write_file> tags
        write_matches = re.finditer(r'<write_file\s+path="([^"]+)"\s*>(.*?)</write_file>', reply_text, re.DOTALL)
        for match in write_matches:
            rel_path, content = match.group(1), match.group(2)
            try:
                target_path = safe_resolve_path(rel_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                applied_files.append(rel_path)
                self.recent_modifications.append({
                    "path": rel_path,
                    "type": "write",
                    "content": content
                })
                self.modification_history.append({
                    "path": rel_path,
                    "type": "write",
                    "content": content
                })
            except Exception as e:
                print(f"Error executing self-modification <write_file path=\"{rel_path}\">: {e}")

        # Parse <patch_file> tags
        patch_matches = re.finditer(r'<patch_file\s+path="([^"]+)"\s*>(.*?)</patch_file>', reply_text, re.DOTALL)
        for match in patch_matches:
            rel_path, patch_content = match.group(1), match.group(2)
            try:
                target_path = safe_resolve_path(rel_path)
                if not target_path.exists():
                    raise FileNotFoundError(f"Cannot patch non-existent file: {target_path}")

                file_content = target_path.read_text(encoding="utf-8")
                blocks = re.findall(r'<<<<(.*?)====(.*?)>>>>', patch_content, re.DOTALL)
                modified = False
                logged_blocks = []
                for search, replace in blocks:
                    search_clean = search.strip("\r\n")
                    replace_clean = replace.strip("\r\n")
                    if search_clean in file_content:
                        file_content = file_content.replace(search_clean, replace_clean, 1)
                        modified = True
                        logged_blocks.append({
                            "search": search_clean,
                            "replace": replace_clean
                        })
                    else:
                        print(f"Patch search block not found in {rel_path}:\n{search_clean}")
                
                if modified:
                    target_path.write_text(file_content, encoding="utf-8")
                    applied_files.append(rel_path)
                    self.recent_modifications.append({
                        "path": rel_path,
                        "type": "patch",
                        "blocks": logged_blocks
                    })
                    self.modification_history.append({
                        "path": rel_path,
                        "type": "patch",
                        "blocks": logged_blocks
                    })
            except Exception as e:
                print(f"Error executing self-modification <patch_file path=\"{rel_path}\">: {e}")

        if applied_files:
            self.virtual_world.update_state("last_interaction", f"Modified {', '.join(applied_files)}")
            for f in applied_files:
                if f not in self.virtual_world.state["knowledge_base"]:
                    self.virtual_world.state["knowledge_base"].append(f)

        return applied_files

    def _normalize_command(self, message: str) -> str:
        command = " ".join(message.strip().split())
        
        prefixes = [
            "hey ira, ", "hey ira ", "hey, ira ", "hey, ", "hey ",
            "hello ira, ", "hello ira ", "hello, ira ", "hello, ", "hello ",
            "hi ira, ", "hi ira ", "hi, ira ", "hi, ", "hi ",
            "please ", "can you ", "could you ", "would you ", "ira, ", "ira ", "ira: "
        ]
        
        suffixes = [
            " please", " thank you", " thanks", " now", " for me"
        ]
        
        changed = True
        while changed:
            changed = False
            lowered = command.lower()
            for prefix in prefixes:
                if lowered.startswith(prefix):
                    command = command[len(prefix):].strip()
                    changed = True
                    break
            if changed:
                continue
            
            for suffix in suffixes:
                if lowered.endswith(suffix):
                    command = command[:-len(suffix)].strip()
                    changed = True
                    break
                    
        return command

    def _looks_like_website(self, target: str) -> bool:
        lowered = target.lower()
        return lowered.startswith(("http://", "https://")) or "." in lowered

    def _is_known_folder(self, target: str) -> bool:
        return target.lower().strip() in {
            "desktop",
            "downloads",
            "download",
            "documents",
            "document",
            "pictures",
            "photos",
            "music",
            "videos",
        }

    def _looks_sensitive_or_unsupported(self, lowered: str) -> bool:
        return lowered.startswith(
            (
                "send message",
                "send email",
                "email ",
                "call ",
                "delete ",
                "remove ",
                "move ",
                "buy ",
                "purchase ",
                "pay ",
                "transfer ",
            )
        )

    def _help_text(self) -> str:
        return "\n".join(
            [
                "You can try:",
                "- open notepad",
                "- open calculator",
                "- open downloads",
                "- open website youtube.com",
                "- search for Python tutorials",
                "- open folder C:\\Users\\hp\\Downloads",
                "- open file C:\\path\\to\\file.txt",
                "- play relaxing music",
                "- what time is it",
            ]
        )
