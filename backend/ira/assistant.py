from __future__ import annotations

import subprocess
import time
from datetime import datetime
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Phase 2.5 – Fast local intent router
# Commands in these dicts are resolved locally in O(1) without touching Gemini.
# ---------------------------------------------------------------------------

# Bare names (after "open ") that map directly to a URL.
_FAST_WEBSITE_SHORTCUTS: dict[str, str] = {
    "youtube":       "https://youtube.com",
    "google":        "https://google.com",
    "github":        "https://github.com",
    "gmail":         "https://mail.google.com",
    "google maps":   "https://maps.google.com",
    "whatsapp":      "https://web.whatsapp.com",
    "netflix":       "https://netflix.com",
    "twitter":       "https://twitter.com",
    "x":             "https://x.com",
    "instagram":     "https://instagram.com",
    "reddit":        "https://reddit.com",
    "linkedin":      "https://linkedin.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
}

# Bare names (after "open ") that map to a known executable command.
# These bypass open_app()'s filesystem search entirely.
_FAST_APP_SHORTCUTS: dict[str, str] = {
    "chrome":          "chrome",
    "google chrome":   "chrome",
    "edge":            "msedge",
    "microsoft edge":  "msedge",
    "firefox":         "firefox",
    "calculator":      "calc",
    "calc":            "calc",
    "notepad":         "notepad",
    "paint":           "mspaint",
    "vscode":          "code",
    "vs code":         "code",
    "visual studio code": "code",
    "terminal":        "wt",
    "windows terminal": "wt",
    "cmd":             "cmd",
    "command prompt":  "cmd",
    "powershell":      "powershell",
    "word":            "winword",
    "excel":           "excel",
    "outlook":         "outlook",
}

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
from .memory.context import ContextManager
from .planner.planner import TaskPlanner
from .execution.executor import TaskExecutor
from .goals.manager import GoalManager

# ---------------------------------------------------------------------------
# Phase 6 – Mobile Companion Server
# ---------------------------------------------------------------------------
from .mobile.server import MobileServer
_mobile_server: MobileServer | None = None

def start_mobile_server():
    if _mobile_server:
        _mobile_server.start()

def stop_mobile_server():
    if _mobile_server:
        _mobile_server.stop()

def mobile_server_running() -> bool:
    if _mobile_server:
        return _mobile_server.is_running()
    return False

# ---------------------------------------------------------------------------
# Phase 2.6 – Single shared ContextManager for the lifetime of the process.
# Routing logic never reads from this; it is purely an observation layer.
# ---------------------------------------------------------------------------
_context: ContextManager = ContextManager()

# ---------------------------------------------------------------------------
# Phase 2.7 – Shared TaskPlanner instance
# ---------------------------------------------------------------------------
_planner: TaskPlanner = TaskPlanner()

# ---------------------------------------------------------------------------
# Phase 5.1 – Shared TaskExecutor instance
# ---------------------------------------------------------------------------
_executor: TaskExecutor = TaskExecutor(handler=None)

# ---------------------------------------------------------------------------
# Phase 8.3 – Agent Planning Foundation
# ---------------------------------------------------------------------------
from .agent.planner import AgentPlanner
from .agent.executor import AgentExecutor

_agent_planner: AgentPlanner = AgentPlanner()
_agent_results = {}

def _global_agent_handler(action: str):
    queue = _executor.execute([action])
    task = queue.all()[0]
    from .execution.task import TaskStatus
    if task.status == TaskStatus.FAILED:
        raise RuntimeError(task.error)
    _agent_results[action] = task.result
    return task.result

_agent_executor: AgentExecutor = AgentExecutor(handler=_global_agent_handler)

# ---------------------------------------------------------------------------
# Phase 5.2 – Shared GoalManager instance
# ---------------------------------------------------------------------------
_goal_manager: GoalManager = GoalManager()

def get_goal(goal_id: str):
    return _goal_manager.get(goal_id)

def get_all_goals():
    return _goal_manager.all()

def get_goal_manager():
    return _goal_manager


@dataclass(frozen=True)
class AssistantResponse:
    text: str
    handled: bool = True

# ---------------------------------------------------------------------------
# Phase 7.6 – Skill Framework registration
# ---------------------------------------------------------------------------
from .skills.registry import SkillRegistry
from .skills.system import SystemSkill
from .skills.app import AppSkill
from .skills.browser import BrowserSkill
from .skills.media import MediaSkill

_registry: SkillRegistry = SkillRegistry()
_registry.register(SystemSkill())
_registry.register(BrowserSkill())
_registry.register(AppSkill())
_registry.register(MediaSkill())

def get_skill_registry() -> SkillRegistry:
    """Return the shared SkillRegistry singleton (read-only accessor)."""
    return _registry


class IRAAssistant:
    def __init__(self, conversation: GeminiConversation | None = None) -> None:
        self.conversation = conversation or GeminiConversation()
        from .virtual_world import VirtualWorld
        self.virtual_world = VirtualWorld()
        self.recent_modifications = []
        self.modification_history = []
        self._llm_time: float = 0.0  # seconds; set by _handle_internal when LLM is called

        # Wrapper to translate unhandled responses into exceptions for the executor
        def _exec_handler(cmd: str):
            resp = self._handle_internal(cmd)
            if not resp.handled:
                raise RuntimeError(resp.text)
            return resp
            
        _executor.handler = _exec_handler

        # Initialize MobileServer singleton lazily exactly once
        global _mobile_server
        if _mobile_server is None:
            _mobile_server = MobileServer(self)

    # ------------------------------------------------------------------
    # Public entry point — measures and logs per-stage performance
    # ------------------------------------------------------------------
    def handle(self, message: str) -> AssistantResponse:
        """Profiling wrapper: delegates to _handle_internal and prints [PERF] logs.

        Phase 2.6 – memory integration
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        * Records the incoming user message **before** routing begins.
        * Records the outgoing assistant response **after** routing completes.
        Routing logic itself is not altered.
        """
        # --- memory: record user turn ---
        _context.remember_user(message)

        goal = _goal_manager.create(message)
        plan = _agent_planner.plan(message)

        if len(plan.steps) <= 1:
            _goal_manager.start(goal.id)
            self._llm_time = 0.0
            t_start = time.perf_counter()
            response = self._handle_internal(message)
            t_end   = time.perf_counter()

            total_ms  = (t_end - t_start) * 1000
            llm_ms    = self._llm_time * 1000
            intent_ms = total_ms - llm_ms

            print(f"[PERF] Command processing: {intent_ms:.0f} ms")
            print(f"[PERF] Gemini response generation: {llm_ms:.0f} ms")

            if response.handled:
                _goal_manager.complete(goal.id)
            else:
                _goal_manager.fail(goal.id, response.text)

            # --- memory: record assistant turn ---
            _context.remember_assistant(response.text)

            return response
        else:
            _goal_manager.start(goal.id)
            
            global _agent_results
            _agent_results.clear()
            
            plan = _agent_executor.execute(plan)
            
            results = []
            overall_handled = True
            
            from .agent.step import StepStatus
            for step in plan.all():
                if step.status == StepStatus.FAILED:
                    results.append(f"✗ {step.error}")
                    overall_handled = False
                elif step.status == StepStatus.SKIPPED:
                    pass
                else:
                    res_text = _agent_results.get(step.action, "")
                    results.append(f"✓ {res_text}")
            
            if plan.failed():
                failed_msgs = [str(s.error) for s in plan.failed()]
                _goal_manager.fail(goal.id, "; ".join(failed_msgs))
            else:
                _goal_manager.complete(goal.id)
            
            combined_text = "\n".join(results)
            combined_response = AssistantResponse(combined_text, handled=overall_handled)
            
            # --- memory: record assistant turn ---
            _context.remember_assistant(combined_response.text)
            
            return combined_response

    def _handle_internal(self, message: str) -> AssistantResponse:
        command = self._normalize_command(message)
        lowered = command.lower()
        self.recent_modifications = []

        if not command:
            return AssistantResponse("I'm here. Tell me what you want to do.", handled=False)

        # ------------------------------------------------------------------
        # Phase 2.6 Step 3 – Context resolution (runs before the router).
        # If the command contains a pronoun/reference word and context is
        # available, rewrite it.  If context is missing, return a
        # clarification immediately so Gemini is never called on ambiguity.
        # ------------------------------------------------------------------
        ctx_result = self._resolve_context(command, lowered)
        if isinstance(ctx_result, AssistantResponse):
            return ctx_result          # clarification – stop here
        command, lowered = ctx_result  # possibly rewritten

        try:
            # ------------------------------------------------------------------
            # Phase 7.6 – Skill Registry dispatch
            # Runs after context resolution, before existing fast-path handlers.
            # ------------------------------------------------------------------
            skill = _registry.dispatch(command)
            if skill is not None:
                print(f"[SKILL] Routing '{command}' \u2192 {skill.name}")
                skill_result = skill.execute(command)
                if isinstance(skill_result, AssistantResponse):
                    return skill_result
                return AssistantResponse(str(skill_result))

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

            if lowered in {
                "time", "what time is it", "tell me the time", "current time",
                "time now", "what's the time", "whats the time",
                "tell me the time now", "what is the time", "clock",
            }:
                print("[ROUTER] Fast-path: time query → local")
                return AssistantResponse(f"It is {datetime.now().strftime('%I:%M %p').lstrip('0')}.")

            if lowered in {
                "date today", "today", "what is the date", "what is today's date",
                "what's today's date", "whats today's date", "tell me the date",
                "what is the date today", "date now", "today date",
                "today's date", "todays date",
            }:
                print("[ROUTER] Fast-path: date query → local")
                return AssistantResponse(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.")

            if lowered in {
                "date",
                "what date is it",
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

            if lowered.startswith((
                "sleep", "go to sleep", "put the computer to sleep",
                "hibernate", "go to hibernate", "enter sleep mode", "enter hibernate mode",
                "sleep pc", "sleep my", "sleep the", "sleep computer",
                "sleep my computer", "suspend", "put pc to sleep",
                "put my computer to sleep",
            )):
                print("[ROUTER] Fast-path: sleep → local")
                return AssistantResponse(sleep_system())

            if lowered.startswith((
                "restart", "reboot", "restart computer", "restart the computer",
                "restart my computer", "restart pc", "restart my pc",
            )):
                print("[ROUTER] Fast-path: restart → local")
                try:
                    import os as _os
                    if _os.name != "nt":
                        raise ActionError("Restart is only supported on Windows.")
                    subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
                    return AssistantResponse("Restarting the computer.")
                except subprocess.CalledProcessError:
                    return AssistantResponse("I could not restart the computer.", handled=False)


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
                result = open_app(app_name)      # may raise ActionError
                _context.set_app(app_name)       # only reached on success
                return AssistantResponse(result)

            if lowered.startswith(("open application ", "open app ", "open program ")):
                app_name = command.split(" ", 2)[2].strip()
                result = open_app(app_name)      # may raise ActionError
                _context.set_app(app_name)       # only reached on success
                return AssistantResponse(result)

            if lowered.startswith("go to "):
                target = command[len("go to ") :].strip()
                result = open_website(target)    # may raise ActionError
                _context.set_website(target)     # only reached on success
                return AssistantResponse(result)

            if lowered.startswith("visit "):
                target = command[len("visit ") :].strip()
                result = open_website(target)    # may raise ActionError
                _context.set_website(target)     # only reached on success
                return AssistantResponse(result)

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
                result = open_website(target)    # may raise ActionError
                _context.set_website(target)     # only reached on success
                return AssistantResponse(result)

            if lowered.startswith("open downloads"):
                return AssistantResponse(open_known_folder("downloads"))

            if lowered.startswith("open documents"):
                return AssistantResponse(open_known_folder("documents"))

            if lowered.startswith("open desktop"):
                return AssistantResponse(open_known_folder("desktop"))

            if lowered.startswith("open pictures") or lowered.startswith("open photos"):
                return AssistantResponse(open_known_folder("pictures"))

            # ------------------------------------------------------------------
            # Phase 2.5 – Fast website shortcuts (O(1) dict lookup)
            # Handles bare names: "open github", "open gmail", "open youtube" etc.
            # Placed before the generic "open <target>" handler.
            # ------------------------------------------------------------------
            if lowered.startswith("open "):
                _target_name = lowered[len("open "):].strip()
                if _target_name in _FAST_WEBSITE_SHORTCUTS:
                    _url = _FAST_WEBSITE_SHORTCUTS[_target_name]
                    print(f"[ROUTER] Fast-path: open {_target_name} → website {_url}")
                    result = open_website(_url)
                    _context.set_website(_target_name)
                    return AssistantResponse(result)
                if _target_name in _FAST_APP_SHORTCUTS:
                    _exe = _FAST_APP_SHORTCUTS[_target_name]
                    print(f"[ROUTER] Fast-path: open {_target_name} → app {_exe}")
                    result = open_app(_exe)
                    _context.set_app(_target_name)
                    return AssistantResponse(result)

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
                    result = open_website(target)   # may raise ActionError
                    _context.set_website(target)    # only reached on success
                    return AssistantResponse(result)
                if self._is_known_folder(target):
                    return AssistantResponse(open_known_folder(target))
                result = open_app(target)           # may raise ActionError
                _context.set_app(target)            # only reached on success
                return AssistantResponse(result)

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

    # ------------------------------------------------------------------
    # Phase 2.6 Step 3 – Context-resolution preprocessing
    # ------------------------------------------------------------------

    # Verbs that act on an application referent.
    _APP_VERBS: frozenset[str] = frozenset({
        "close", "minimize", "minimise", "maximize", "maximise",
        "restore", "focus", "switch to", "reopen", "relaunch",
    })

    # Verbs that act on a website referent.
    _WEB_VERBS: frozenset[str] = frozenset({
        "refresh", "reload", "go back", "go forward",
        "open again", "reopen", "revisit",
    })

    # Words that trigger context look-up when they appear as the object.
    _CONTEXT_TRIGGERS: tuple[str, ...] = (
        " it", " this", " that", " them", " again",
        " the previous", " the same",
    )

    def _resolve_context(
        self, command: str, lowered: str
    ) -> tuple[str, str] | AssistantResponse:
        """Attempt to rewrite a pronoun-bearing command using remembered context.

        Returns
        -------
        tuple[str, str]
            ``(resolved_command, resolved_lowered)`` — the (possibly rewritten)
            command pair.  When no context word is present this is just the
            original pair, unchanged.
        AssistantResponse
            A clarification response when a context word is found but the
            referent cannot be determined unambiguously.  The caller must
            return this immediately and skip routing.
        """
        # Fast exit – no pronoun / reference word in the command at all.
        if not any(trigger in lowered for trigger in self._CONTEXT_TRIGGERS):
            return command, lowered

        state = _context.state

        # ------------------------------------------------------------------
        # Determine the verb (what the user wants to do).
        # ------------------------------------------------------------------
        verb: str | None = None
        for v in self._APP_VERBS | self._WEB_VERBS:
            if lowered.startswith(v + " ") or lowered == v:
                verb = v
                break
        # Special multi-word verbs checked separately
        for mv in ("switch to", "go back", "go forward", "open again"):
            if lowered.startswith(mv):
                verb = mv
                break

        if verb is None:
            # There is a trigger word but we cannot identify the verb;
            # let the router / Gemini handle it normally.
            return command, lowered

        # ------------------------------------------------------------------
        # Choose which referent to use based on the verb category.
        # ------------------------------------------------------------------
        is_web_verb = verb in self._WEB_VERBS
        is_app_verb = verb in self._APP_VERBS

        # Some verbs can apply to either; prefer the most recently set one.
        referent: str | None = None
        if is_web_verb:
            referent = state.last_website
        elif is_app_verb:
            referent = state.last_app
        else:
            # Ambiguous – prefer whichever was set more recently.
            referent = state.last_app or state.last_website

        if not referent:
            # No context available – ask for clarification.
            verb_display = verb.capitalize()
            print("[CTX] No context available for pronoun resolution")
            clarifications = {
                "close":      "What would you like me to close?",
                "minimize":   "What would you like me to minimize?",
                "minimise":   "What would you like me to minimize?",
                "maximize":   "What would you like me to maximize?",
                "maximise":   "What would you like me to maximize?",
                "restore":    "What would you like me to restore?",
                "focus":      "Which application should I focus?",
                "switch to":  "Which application would you like to switch to?",
                "reopen":     "What would you like me to reopen?",
                "relaunch":   "What would you like me to relaunch?",
                "refresh":    "Which website would you like me to refresh?",
                "reload":     "Which website would you like me to reload?",
                "revisit":    "Which website would you like me to revisit?",
                "open again": "Which website or application would you like me to open again?",
            }
            msg = clarifications.get(verb, f"What would you like me to {verb}?")
            return AssistantResponse(msg, handled=False)

        # ------------------------------------------------------------------
        # Rewrite: strip the trailing pronoun/trigger and append the referent.
        # ------------------------------------------------------------------
        rewritten = lowered
        for trigger in self._CONTEXT_TRIGGERS:
            if rewritten.endswith(trigger):
                rewritten = rewritten[: -len(trigger)].strip()
                break

        resolved = f"{rewritten} {referent}"
        print(f'[CTX] Resolved "{command}" -> "{resolved}" (referent: {referent!r})')
        return resolved, resolved.lower()


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


# ---------------------------------------------------------------------------
# Phase 2.6 – Public accessors for the shared ContextManager singleton.
# These are intentionally read-only helpers; they never mutate state.
# ---------------------------------------------------------------------------

def get_context() -> ContextManager:
    """Return the module-level :class:`ContextManager` instance.

    Gives future phases a single, stable reference to the full context
    without exposing the private ``_context`` name directly.
    """
    return _context


def get_last_command() -> str | None:
    """Return the most recent user command recorded in memory, or *None*."""
    return _context.state.last_command


def get_last_app() -> str | None:
    """Return the most recently set application name, or *None*."""
    return _context.state.last_app
