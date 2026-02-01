# Unified Display - Quick Reference

## For Users (Running the Bot)

### Starting the Bot
```bash
cd /home/skahler/workspace/crawl_navigator
./venv/bin/python main.py --steps 10
```

### What You'll See
- **Top**: Full Crawl game screen (normal game TUI)
- **Bottom**: 12-line bot activity panel with timestamped messages

### Activity Panel Shows
- What the bot is doing (moving, detecting enemies, picking up items)
- When state changes occur (starting gameplay, leveling up)
- Warnings (hostile enemies detected, low health)
- Success messages (level up, enemy defeated)

### No Configuration Needed
- Display automatically activates when bot runs
- No special options or setup required
- Works with existing `main.py` commands

---

## For Developers (Extending the Bot)

### Adding Activity Logging

Add logging calls anywhere in `bot.py` to show actions in the activity panel:

```python
# Import already included at top of file:
# from bot_unified_display import UnifiedBotDisplay

# In __init__, instance already created:
# self.unified_display = UnifiedBotDisplay()

# Use the helper method anywhere in the class:

# Log a success
self._log_activity("Enemy defeated!", "success")

# Log normal action
self._log_activity("Moved north to explore", "info")

# Log warning
self._log_activity("Health critically low (3/20)", "warning")

# Log debug info
self._log_activity("Parser detected 2048 bytes of output", "debug")

# Log error
self._log_activity("Move failed: blocked by wall", "error")
```

### Activity Log Levels

```python
level = "success"   # ✓ Green - Achievements, goals reached
level = "info"      # ℹ Default - Normal actions, state changes
level = "warning"   # ⚠ Yellow - Cautions, potential issues
level = "error"     # ✗ Red - Errors, failures
level = "debug"     # ⚙ Cyan - Technical details, diagnostics
```

### Key Methods

```python
# Add an activity message
self._log_activity(message: str, level: str = "info") -> None

# Direct access to unified_display object
self.unified_display.add_activity(message, level)
self.unified_display.get_activity_history(count)
self.unified_display.display(visual_screen, move_count, action, state, health)
```

### Placement Strategy

Add activity logging to:

1. **State Machine Transitions**
   ```python
   def on_enter_gameplay(self):
       self._log_activity("Entered GAMEPLAY state", "success")
   ```

2. **Key Actions**
   ```python
   def move_player(self, direction):
       self._log_activity(f"Moving {direction}", "info")
   ```

3. **Danger Detection**
   ```python
   if enemy_detected:
       self._log_activity(f"⚠ {enemy_type} detected at ({x}, {y})", "warning")
   ```

4. **Achievements**
   ```python
   if level_up:
       self._log_activity(f"✓ Level up! Now level {new_level}", "success")
   ```

---

## File References

### Main Implementation Files
- [bot_unified_display.py](bot_unified_display.py) - Display engine (227 lines)
- [bot.py](bot.py) - Integration point (lines 19, 94, 283-338, 1295, 1335, 1346, 1367)

### Documentation
- [UNIFIED_DISPLAY_IMPLEMENTATION.md](UNIFIED_DISPLAY_IMPLEMENTATION.md) - Complete technical overview
- [UNIFIED_DISPLAY_EXAMPLES.md](UNIFIED_DISPLAY_EXAMPLES.md) - Visual examples and screenshots

### Tests
- [tests/test_bot.py](tests/test_bot.py) - All 11 tests pass ✓

---

## Current Activity Logging Points

### Startup Sequence (already implemented)
```
[HH:MM:SS] ✓ Startup menu detected          (line 1295)
[HH:MM:SS] ℹ Sending character name: {name}  (line 1335)
[HH:MM:SS] ℹ Selecting 'Dungeon Crawl'...    (line 1346)
[HH:MM:SS] ✓ Gameplay started!              (line 1367)
```

### Recommended Next Additions
- Gameplay state entered
- Movement actions (north, south, east, west)
- Enemy detection and distance
- Item discovery and pickup
- Level ups and stat changes
- Health state changes
- Combat actions (attack, dodge)
- Spell casting
- Rest/wait actions

---

## Testing

### Run All Tests
```bash
./venv/bin/python -m pytest tests/test_bot.py -v
```

### Result
```
tests/test_bot.py::TestBotInitialization::test_bot_initializes PASSED
tests/test_bot.py::TestBotInitialization::test_bot_has_char_creation_state PASSED
tests/test_bot.py::TestBotInitialization::test_char_creation_state_is_state_machine PASSED
tests/test_bot.py::TestBotInitialization::test_bot_has_required_attributes PASSED
tests/test_bot.py::TestBotInitialization::test_startup_sequence_uses_correct_attribute PASSED
tests/test_bot.py::TestLoginSequence::test_startup_screen_detection PASSED
tests/test_bot.py::TestLoginSequence::test_menu_screen_detection PASSED
tests/test_bot.py::TestLoginSequence::test_character_creation_flow_startup_to_race PASSED
tests/test_bot.py::TestLoginSequence::test_full_character_creation_sequence PASSED
tests/test_bot.py::TestLoginSequence::test_state_machine_reset_to_startup PASSED
tests/test_bot.py::TestLoginSequence::test_gameplay_detection_from_state_machine PASSED

======================== 11 passed in 0.95s ========================
```

---

## Troubleshooting

### Issue: Activity panel not showing
**Solution**: Check terminal height is at least 30 lines. The unified display needs space for game screen + separator + activity panel.

### Issue: Messages truncated
**Solution**: This is intentional. Full messages are logged by loguru. Get full history programmatically:
```python
full_history = self.unified_display.get_activity_history(100)
```

### Issue: No colors showing
**Solution**: Terminal doesn't support ANSI colors. Most modern terminals do - check terminal settings or use a different terminal emulator.

### Issue: Performance slow
**Solution**: Unlikely - activity panel is very lightweight. Check if game is actually responsive by checking game screen updates.

---

## Summary

| Aspect | Status | Details |
|--------|--------|---------|
| Display created | ✓ | bot_unified_display.py (227 lines) |
| Bot integrated | ✓ | Imports, init, methods all in place |
| Tests passing | ✓ | All 11 tests pass |
| Startup logging | ✓ | 4 key startup events logged |
| Ready to use | ✓ | Just run `python main.py` |
| Extensible | ✓ | Easy to add logging anywhere |

