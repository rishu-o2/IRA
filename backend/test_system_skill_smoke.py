import sys
sys.path.insert(0, r'c:\Users\hp\IRA\backend')

from ira.skills.system import SystemSkill
import ira.actions as actions

# Monkeypatch actions to prevent actual system modifications
actions.lock_screen = lambda: "Locking the screen."
actions.shutdown_system = lambda: "Shutting down the computer."
actions.sleep_system = lambda: "Putting the computer to sleep."
actions.mute_system = lambda: "Muting the volume."
actions.volume_up = lambda: "Increasing volume."
actions.volume_down = lambda: "Decreasing volume."
actions.set_brightness = lambda l: f"Screen brightness set to {l}%."

import subprocess
# Monkeypatch subprocess to prevent actual restart
subprocess.run = lambda *args, **kwargs: None

skill = SystemSkill()

print("--- Testing SystemSkill ---")

assert skill.name == "system"
print("Name: PASSED")

# Test lock screen
assert skill.can_handle("lock screen")
r1 = skill.execute("lock screen")
assert r1.text == "Locking the screen."
assert r1.handled is True
print("Lock Screen: PASSED")

# Test mute volume
assert skill.can_handle("mute volume")
r2 = skill.execute("mute volume")
assert r2.text == "Muting the volume."
assert r2.handled is True
print("Mute Volume: PASSED")

# Test set brightness to 50
assert skill.can_handle("set brightness to 50")
r3 = skill.execute("set brightness to 50")
assert r3.text == "Screen brightness set to 50%."
assert r3.handled is True
print("Set Brightness: PASSED")

# Test restart
assert skill.can_handle("restart the computer")
r4 = skill.execute("restart the computer")
assert r4.text == "Restarting the computer."
assert r4.handled is True
print("Restart: PASSED")

# Test unknown
assert not skill.can_handle("open chrome")
print("Unknown rejection: PASSED")

print("\nAll SystemSkill tests PASSED.")
