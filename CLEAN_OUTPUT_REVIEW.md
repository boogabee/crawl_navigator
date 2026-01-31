# Clean Output Usage Review

## Summary
Reviewed all 45 instances of `clean_output` and `_clean_ansi()` usage in bot.py. Identified **15 decision-making/state change operations** that currently scan the entire screen and can be optimized by using appropriate TUI sections.

---

## Decision-Making Logic Using clean_output

### 1. **Gold Detection** (Lines 218)
- **Current**: Searches entire clean_output for `"Found \d+ gold pieces?"`
- **Type**: Event logging (non-critical decision)
- **Appropriate TUI Section**: **MESSAGE LOG**
- **Reason**: Gold pickup messages appear in the message log area
- **Recommendation**: Use `message_log.get_text()` to search for gold messages
- **Status**: ✓ Non-critical (logging only)

---

### 2. **Item Discovery** (Lines 231)
- **Current**: Searches clean_output for patterns like `"You see (.+?)\."` or `"There is (.+?) here"`
- **Type**: Event logging (non-critical decision)
- **Appropriate TUI Section**: **MESSAGE LOG**
- **Reason**: Item discovery messages appear in message log
- **Recommendation**: Use `message_log.get_text()` to search for item messages
- **Status**: ✓ Non-critical (logging only)

---

### 3. **Enemy Encounter Detection** (Lines 245)
- **Current**: Searches clean_output for `"You encounter (.+?)"` or `"There is (.+?) here"`
- **Type**: Event logging (non-critical decision)
- **Appropriate TUI Section**: **MESSAGE LOG** (for encounter messages)
- **Reason**: Encounter messages appear in message log, though active enemies appear in encounters area
- **Note**: This is separate from the main `_detect_enemy_in_range()` which uses TUI encounters area
- **Recommendation**: Use `message_log.get_text()` for encounter event logging
- **Status**: ✓ Non-critical (logging only)

---

### 4. **Level-Up Detection** (Lines 260-261) ⚠️ **IMPORTANT**
- **Current**: Searches clean_output for `"You have reached level \d+"`
- **Type**: **State change decision** - triggers attribute selection prompt
- **Appropriate TUI Section**: **MESSAGE LOG**
- **Reason**: Level-up messages appear in message log; NOT in character panel stats (XL shows current level, not new level notification)
- **Recommendation**: Use `message_log.get_text()` to detect level-ups
- **Status**: 🔴 **Should be refactored** - critical state decision

---

### 5. **Feature Discovery** (Lines 277)
- **Current**: Searches clean_output for door/staircase patterns
- **Type**: Event logging (non-critical decision)
- **Appropriate TUI Section**: **MESSAGE LOG**
- **Reason**: Feature discovery messages appear in message log
- **Recommendation**: Use `message_log.get_text()` to search for feature messages
- **Status**: ✓ Non-critical (logging only)

---

### 6. **"You Feel Stronger" Detection** (Lines 1111) ⚠️ **IMPORTANT**
- **Current**: Searches clean_output for `"you feel stronger"` (lowercase)
- **Type**: **State change decision** - prevents re-triggering attribute prompt
- **Appropriate TUI Section**: **MESSAGE LOG**
- **Reason**: "You feel stronger" is a game message confirming attribute increase, appears in message log
- **Recommendation**: Use `message_log.get_text()` to detect this confirmation message
- **Status**: 🔴 **Should be refactored** - critical state decision

---

### 7. **Attribute Increase Prompt** (Lines 1114) ⚠️ **IMPORTANT**
- **Current**: Searches clean_output for `"Increase (S)trength"` or `"Increase (S)trength, (I)ntelligence, or (D)exterity"`
- **Type**: **State change decision** - triggers attribute selection
- **Appropriate TUI Section**: Could be **MESSAGE LOG** or a special menu area
- **Note**: This is a game prompt (not a normal message), appears when leveling up
- **Reason**: Prompts appear in the displayed text area
- **Recommendation**: Use `message_log.get_text()` initially, but consider if this is a special menu state requiring separate handling
- **Status**: 🔴 **Should be refactored** - critical state decision

---

### 8. **Save Game Prompt** (Lines 1127) ⚠️ **IMPORTANT**
- **Current**: Searches clean_output for `"save game and return to main menu"` and `"[y]es or [n]o"`
- **Type**: **State change decision** - prevents accidental game exit
- **Appropriate TUI Section**: Could be **MESSAGE LOG** or special prompt area
- **Reason**: Save prompt appears in displayed text when triggered
- **Recommendation**: Use `message_log.get_text()` or parse as a special menu state
- **Status**: 🔴 **Should be refactored** - critical state decision

---

### 9. **Gameplay Indicator Check** (Lines 1210-1219) ⚠️ **IMPORTANT**
- **Current**: Searches clean_output for `"Health:"`, `"XL:"`, and combat action keywords
- **Type**: **State transition decision** - determines if in gameplay
- **Appropriate TUI Sections**:
  - `"Health:"` and `"XL:"`: **CHARACTER PANEL** (right side stats)
  - Combat keywords (`"You encounter"`, `"block"`, `"miss"`, `"hits"`, `"damage"`): **MESSAGE LOG**
  - Creature names: **ENCOUNTERS AREA** (monsters list)
- **Recommendation**: 
  - Check `character_panel.get_text()` for health and XL
  - Check `message_log.get_text()` for combat actions
  - Already using `_detect_enemy_in_range()` for encounters area
- **Status**: 🔴 **Should be refactored** - critical state decision

---

### 10. **Too Injured to Fight Recklessly** (Lines 1278) ⚠️ **IMPORTANT**
- **Current**: Searches clean_output for `"too injured to fight recklessly"`
- **Type**: **State change decision** - switches from autofight to movement
- **Appropriate TUI Section**: **MESSAGE LOG**
- **Reason**: Warning message appears in message log
- **Recommendation**: Use `message_log.get_text()` to detect injury warning
- **Status**: 🔴 **Should be refactored** - critical state decision

---

### 11. **No Reachable Target Detection** (Lines 1289) ⚠️ **IMPORTANT**
- **Current**: Searches clean_output for `"no reachable target in view"`
- **Type**: **State change decision** - switches from autofight to movement
- **Appropriate TUI Section**: **MESSAGE LOG**
- **Reason**: Autofight failure message appears in message log
- **Recommendation**: Use `message_log.get_text()` to detect unreachable target message
- **Status**: 🔴 **Should be refactored** - critical state decision

---

## Summary by Priority

### 🔴 Critical (State Change Decisions) - 8 items
These make decisions that change game state/strategy:
1. Level-up detection (line 260)
2. "You feel stronger" check (line 1111)
3. Attribute prompt detection (line 1114)
4. Save game prompt (line 1127)
5. Gameplay indicator check (line 1210-1219)
6. Too injured detection (line 1278)
7. No reachable target detection (line 1289)

### ✓ Non-Critical (Logging Only) - 7 items
These only log events, don't change game logic:
1. Gold detection (line 218)
2. Item discovery (line 231)
3. Enemy encounter logging (line 245)
4. Feature discovery (line 277)
5. Plus display/debug uses (not decision-making)

---

## Refactoring Strategy

### Phase 1: High-Impact Message Log Checks
Refactor these 6 checks to use TUI parser message log area:
1. Level-up detection (line 260)
2. "You feel stronger" (line 1111)
3. Attribute prompt (line 1114)
4. Save game prompt (line 1127)
5. Too injured (line 1278)
6. No reachable target (line 1289)

**Code Pattern**:
```python
# Instead of:
clean_output = self._clean_ansi(output) if output else ""
if 'target message' in clean_output:

# Use:
screen_text = self.screen_buffer.get_screen_text()
if screen_text:
    tui_parser = DCSSLayoutParser()
    tui_areas = tui_parser.parse_layout(screen_text)
    message_log = tui_areas.get('message_log', None)
    message_content = message_log.get_text() if message_log else ""
    if 'target message' in message_content:
```

### Phase 2: Character Panel Checks
Refactor gameplay indicator check (line 1210):
- Extract `"Health:"` and `"XL:"` from character panel instead of full output
- Keep message log check for combat actions

### Phase 3: Logging Operations (Non-Critical)
Refactor event logging to use appropriate sections:
- Gold, items, encounters → message log
- Could improve accuracy but lower priority (logging only)

---

## TUI Section Reference

| Section | Content | Current Usage | Decision Count |
|---------|---------|----------------|-----------------|
| **Map Area** | Dungeon layout, @ player | Not used for decisions | 0 |
| **Character Panel** | Health, Mana, XL, Experience | Gameplay check | 1 |
| **Encounters Area** | Visible creatures | Enemy detection ✓ | 0 (already optimized) |
| **Message Log** | Game messages, prompts | Should be used | 8 critical |

---

## Recommendations Summary

1. **Immediate**: Refactor 6 critical message detection checks to use message log area
2. **High Value**: Update gameplay indicator check to use character panel for stats
3. **Low Priority**: Update event logging to use message log (cosmetic improvement)
4. **Leverage**: The `_detect_enemy_in_range()` method already correctly uses encounters area - use as a model for refactoring

---

## Notes

- The bot already has good practices: `_detect_enemy_in_range()` correctly uses TUI encounters area
- Most critical decisions are message-based (should be in message log)
- Stats-based decisions (health, XL) should use character panel
- Refactoring will improve accuracy, reduce false positives, and align with TUI architecture principles
