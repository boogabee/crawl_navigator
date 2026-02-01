# Inventory Screen Detection & Handling - v1.7

## Summary

Created fixture tests for inventory screen detection and implemented robust inventory screen handling to prevent bot from getting stuck when inventory screen appears.

## Fixtures Created

Created two inventory screen test fixtures in `tests/fixtures/game_screens/`:
- **inventory_screen.txt** - Basic inventory with 4 items (Hand Weapons, Armour, Potions)
- **inventory_screen_full.txt** - Full inventory with 6 items (added Jewellery, Scrolls sections)

These fixtures allow testing inventory detection logic without relying on actual game runs.

## Key Improvements

### 1. Inventory State Tracking
**File**: `bot.py` - `_refresh_inventory()` method (lines 1198-1213)

Added `self.last_inventory_refresh = self.move_count` when opening inventory:
```python
def _refresh_inventory(self) -> Optional[str]:
    self.in_inventory_screen = True
    self.last_inventory_refresh = self.move_count  # NOW SETS TIMESTAMP
    logger.info("📋 Opening inventory screen")
    return self._return_action('i', "Refreshing inventory display")
```

This timestamp enables timeout protection if inventory screen fails to appear.

### 2. Proactive Inventory Detection
**File**: `bot.py` - `_decide_action()` method (lines 1650-1668)

Added proactive inventory screen detection BEFORE flag-based checking:
```python
# CHECK FOR INVENTORY SCREEN - PARSE AND EXIT
# First, check if we're ALREADY in an inventory screen (proactive check)
proactive_inventory_action = self._check_and_handle_inventory_state(output)
if proactive_inventory_action:
    self.in_inventory_screen = False  # Clear flag after handling
    return proactive_inventory_action
```

This catches inventory screens that appear unexpectedly (not due to 'i' command).

### 3. Fallback Detection for Unexpected Inventory
**File**: `bot.py` - `_check_and_handle_inventory_state()` method (lines 1255-1261)

Added warning log when inventory is detected without prior flag:
```python
if in_inventory:
    # Mark that we're now in inventory screen if we weren't before
    # This catches cases where inventory appears unexpectedly
    if not self.in_inventory_screen:
        logger.info("⚠️ Detected inventory screen without prior 'i' command - handling anyway")
        self.in_inventory_screen = True
```

Ensures bot can recover from unexpected inventory screens.

### 4. Timeout Protection
**File**: `bot.py` - `_decide_action()` method (lines 1664-1668)

If inventory flag is set but screen doesn't appear after 3 moves, reset:
```python
if self.move_count > self.last_inventory_refresh + 3:
    logger.warning("⚠️ Timeout waiting for inventory screen, continuing anyway")
    self.in_inventory_screen = False
else:
    logger.debug("Waiting for inventory screen to appear...")
    return self._return_action('.', "Waiting for inventory screen")
```

Prevents infinite waits if inventory screen fails to appear.

## Test Coverage

**File**: `tests/test_inventory_detection.py` - 8 new tests
- `test_inventory_fixture_basic_exists` ✓
- `test_inventory_fixture_full_exists` ✓
- `test_inventory_detection_basic` ✓ (detects and exits inventory)
- `test_inventory_detection_full` ✓ (handles multiple items)
- `test_inventory_flag_set_on_refresh` ✓ (flag properly managed)
- `test_inventory_cooldown_tracking` ✓ (timeout protection works)
- `test_inventory_item_line_detection` ✓ (item parsing correct)
- `test_no_false_positive_on_game_screen` ✓ (no false alarms)

**Total Tests**: 146 passing (138 → 146 after adding 8 new inventory tests)

## Verification

Tested with real gameplay:
- **Run 1 (100 steps)**: Completed successfully, no inventory loops, character reached Level 1
- **Run 2 (150 steps, timeout 120s)**: Completed 100+ moves, reached Level 2, 19/24 health
- **Run 3 (100 steps)**: Completed successfully with active combat against hobgoblins

All test runs completed without getting stuck in inventory screen loops.

## Architecture Notes

The inventory detection system now works in layers:

1. **Proactive Detection** - Runs on every decision, checks if current screen is inventory (even if flag not set)
2. **Flag-Based Tracking** - Maintains `in_inventory_screen` flag for explicit 'i' command handling
3. **Fallback Recovery** - If unexpected inventory detected, captures and handles it
4. **Timeout Protection** - Prevents infinite waits with 3-move timeout

This multi-layer approach ensures the bot can recover from various inventory-related issues without getting stuck.

## Files Modified

1. **bot.py**
   - Line 148: Initialized `last_inventory_refresh = 0`
   - Lines 1206: Added timestamp tracking in `_refresh_inventory()`
   - Lines 1255-1261: Added fallback detection in `_check_and_handle_inventory_state()`
   - Lines 1650-1668: Added proactive detection and timeout in `_decide_action()`

2. **tests/test_inventory_detection.py** (NEW)
   - Created 8 test cases for inventory detection scenarios
   - Validates fixture loading and parsing
   - Tests state management and timeout behavior

3. **tests/fixtures/game_screens/** (NEW)
   - `inventory_screen.txt` - Basic inventory fixture
   - `inventory_screen_full.txt` - Complex inventory fixture

## Backwards Compatibility

All changes are fully backwards compatible:
- Existing game logic unchanged
- Only enhanced with better inventory detection
- Previous bot behavior preserved for non-inventory cases
- No breaking changes to API

## Version

This fix is part of **v1.7** (January 31, 2026) inventory screen reliability improvements.
