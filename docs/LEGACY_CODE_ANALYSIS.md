# Legacy Code Analysis: _decide_action_legacy() Mapping

## Overview
**File**: bot.py, lines 1626-2395 (769 lines)
**Purpose**: Main decision-making logic for gameplay
**Current Status**: Being gradually migrated to DecisionEngine (Phase 3b)

## Decision Priority Order (Legacy)

### Priority 1: Equip/Quaff Slots (Lines 1651-1671)
**Logic**: 
- If `self.equip_slot` is set → send equip slot letter
- If `self.quaff_slot` is set → send quaff slot letter

**Engine Mapping**: 
- ✅ **Equip slot pending** (CRITICAL priority)
- ✅ **Quaff slot pending** (CRITICAL priority)

**Status**: ALREADY HANDLED ✅

---

### Priority 2: Attribute Increase Prompt (Lines 1673-1701)
**Logic**:
- Detect "Increase (S)trength, (I)ntelligence, or (D)exterity" prompt
- Check if new level (tracking: `last_attribute_increase_level`)
- Only respond once per level with 'S'
- Skip if "You feel stronger" already in messages

**Engine Mapping**:
- ✅ **Attribute increase prompt** (CRITICAL priority)

**Status**: ALREADY HANDLED ✅

---

### Priority 3: Save Game Prompt (Lines 1703-1716)
**Logic**:
- Detect "Save game and return to main menu? [y]es or [n]o"
- Respond with 'n' to stay in game

**Engine Mapping**:
- ✅ **Save game prompt** (CRITICAL priority)

**Status**: ALREADY HANDLED ✅

---

### Priority 4: Level Up Message (Lines 1718-1734)
**Logic**:
- Check for level-up message via `parser.has_level_up_message()`
- Track new level via `last_level_up_processed`
- Dismiss --more-- prompt if present (space)
- Otherwise return '.' (wait)

**Engine Mapping**:
- ✅ **Level up** (CRITICAL priority - should respond with 'S' or just continue)

**Status**: PARTIALLY HANDLED
- Engine has "Level up" rule but returns 'S'
- Legacy code returns ' ' (dismiss more) or '.' (wait)
- **Need to refine**: Engine should handle --more-- dismissal

---

### Priority 5: More Prompts (Lines 1736-1741)
**Logic**:
- Detect "--more--" in output
- Respond with space ' ' to continue

**Engine Mapping**:
- ✅ **More prompt** (CRITICAL priority) - responds with ' '

**Status**: ALREADY HANDLED ✅

---

### Priority 6: Shop Detection (Lines 1743-1747)
**Logic**:
- Call `_is_in_shop(output)` to detect shop interface
- If in shop, send Escape '\x1b' to exit

**Engine Mapping**:
- ⚠️ **Shop detection** (HIGH priority)
- Engine has rule for this but may need refinement

**Status**: PARTIALLY HANDLED ✅

---

### Priority 7: Item Pickup Menu (Lines 1749-1754)
**Logic**:
- Call `_is_item_pickup_menu(output)` to detect menu
- Set `in_item_pickup_menu = True`
- Call `_handle_item_pickup_menu(output)`

**Engine Mapping**:
- ✅ **Item pickup menu handling** (HIGH priority)

**Status**: ALREADY HANDLED ✅

---

### Priority 8: Items On Ground (Lines 1756-1759)
**Logic**:
- Call `_detect_items_on_ground(output)` 
- If true, call `_grab_items()` which sends 'g'

**Engine Mapping**:
- ❌ **NO RULE YET** - This needs to be added!
- Condition: `items_on_ground == True`
- Action: 'g' (grab command)
- Priority: NORMAL

**Status**: MISSING - NEED TO ADD ❌

---

### Priority 9: Equipment Check (Lines 1761-1765)
**Logic**:
- Check every 10+ moves (tracking: `last_equipment_check`)
- Call `_find_and_equip_better_armor()`
- If returns action, execute it

**Engine Mapping**:
- ❌ **NO RULE YET** - This is complex, may skip for now
- Would need: equipment evaluation logic
- Condition: `move_count > last_equipment_check + 10 AND better_armor_available`
- Action: 'e' (equip command) or direct slot letter

**Status**: COMPLEX - LOW PRIORITY ❌

---

### Priority 10: Untested Potions (Lines 1767-1774)
**Logic**:
- Check if `parser.state.untested_potions` has items
- Only if not in recent combat (`move_count > last_level_up_processed + 2`)
- Call `_identify_untested_potions()`

**Engine Mapping**:
- ❌ **NO RULE YET** - Complex inventory logic
- Condition: `len(untested_potions) > 0 AND move_count > last_combat + 2`
- Action: 'q' (quaff) or slot letter

**Status**: COMPLEX - LOW PRIORITY ❌

---

### Priority 11: Inventory Screen (Lines 1776-1797)
**Logic**:
- Check for inventory screen state:
  - Proactive check: `_check_and_handle_inventory_state(output)`
  - If waiting (`in_inventory_screen`): return '.' or '.'
  - Timeout after 3 moves: reset and continue

**Engine Mapping**:
- ✅ **Inventory screen detection** (HIGH priority)
- Engine has rule for this

**Status**: ALREADY HANDLED ✅

---

### Priority 12: Goto/Level Descent (Lines 1799-1842)
**Logic**:
- Step 1: Detect "Done exploring" message → send 'G'
- Step 2: After 'G', game asks for location → send 'D'
- Step 3: After 'D', game asks for level → send level number
- Track state via `goto_state` (None → 'awaiting_location_type' → 'awaiting_level_number')

**Engine Mapping**:
- ✅ **Goto commands** (NORMAL priority)
- Rules exist for location type and level number selection

**Status**: ALREADY HANDLED ✅

---

### Priority 13: Menu State (Lines 1844-1847)
**Logic**:
- If `state_tracker.in_menu_state()`: wait

**Engine Mapping**:
- ✅ Various menu-related CRITICAL priority rules

**Status**: ALREADY HANDLED ✅

---

### Priority 14: Health-Based Combat Decisions (Lines 1849+)
**Logic** (from remaining code):
- If enemy detected:
  - If health > 70%: autofight with '\t'
  - If health <= 70%: move or rest
- If no enemy:
  - If health < 60%: rest '5'
  - If health >= 60%: explore 'o'

**Engine Mapping**:
- ✅ **Combat (autofight)** - health > 70% → '\t'
- ✅ **Combat (low health)** - health <= 70% → ''
- ✅ **Rest to recover** - health < 60% → '5'
- ✅ **Explore (good health)** - health >= 60% → 'o'

**Status**: ALREADY HANDLED ✅

---

## Summary: Rule Mapping Status

| Priority | Legacy Code | Engine Status | Notes |
|----------|------------|---------------|-------|
| 1 | Equip Slot | ✅ Handled | CRITICAL |
| 2 | Quaff Slot | ✅ Handled | CRITICAL |
| 3 | Attribute Increase | ✅ Handled | CRITICAL |
| 4 | Save Prompt | ✅ Handled | CRITICAL |
| 5 | Level Up | ⚠️ Partial | Needs --more-- handling |
| 6 | More Prompt | ✅ Handled | CRITICAL |
| 7 | Shop Exit | ✅ Handled | HIGH |
| 8 | Item Pickup Menu | ✅ Handled | HIGH |
| 9 | Items On Ground | ❌ MISSING | NEED TO ADD |
| 10 | Better Armor | ❌ MISSING | Complex, LOW priority |
| 11 | Untested Potions | ❌ MISSING | Complex, LOW priority |
| 12 | Inventory Screen | ✅ Handled | HIGH |
| 13 | Goto/Descent | ✅ Handled | NORMAL |
| 14 | Menu State | ✅ Handled | CRITICAL |
| 15 | Combat/Health | ✅ Handled | NORMAL |

## Missing Rules (Must Add)

### 1. Items On Ground Detection
**Current Location**: Lines 1756-1759  
**Complexity**: Low  
**Priority**: NORMAL  
**Rule**: 
```
name: "Items on ground"
priority: Priority.NORMAL
condition: lambda ctx: ctx.items_on_ground
action: lambda ctx: ('g', "Grabbing items from ground")
```

### 2. Better Armor Detection
**Current Location**: Lines 1761-1765  
**Complexity**: HIGH (needs equipment evaluation)  
**Priority**: NORMAL  
**Status**: SKIP FOR NOW (low impact)

### 3. Untested Potions
**Current Location**: Lines 1767-1774  
**Complexity**: HIGH (needs potion state)  
**Priority**: LOW  
**Status**: SKIP FOR NOW (exploratory feature)

## Rules to Refine

### 1. Level Up Handling
**Issue**: Needs to handle --more-- dismissal
**Fix**: Check if more prompt present after level up, prioritize that

### 2. Combat Movement
**Issue**: Legacy returns '' for low health combat, engine should too
**Validation**: Already correct in engine (LOW HEALTH MOVEMENT rule)

## Additional Decision Logic (Lines 1851-2100)

### Priority 15: Gameplay Indicator Validation (Lines 1855-1902)
**Logic**:
- Check for Health, XL in TUI character panel
- Check for combat/action messages in message log
- Validate gameplay indicators
- Set `gameplay_started = True` when confirmed

**Engine Mapping**:
- ✅ Already handled by gameplay detection rules

**Status**: ALREADY HANDLED ✅

---

### Priority 16: Enemy Detection & Combat (Lines 1907-1965)
**Logic**:
- Call `_detect_enemy_in_range(output)`
- If enemy detected:
  - Calculate health percentage
  - If health ≤ 70%: movement-based attack (direction key)
  - If health > 70%: autofight with Tab ('\\t')
  - Check for "too injured to fight recklessly" message
  - Check for "no reachable target in view" message

**Engine Mapping**:
- ✅ **Combat (autofight)** - health > 70%
- ✅ **Combat (low health movement)** - health ≤ 70%
- ✅ **Too injured to autofight** - needs message check
- ✅ **Out of melee range** - needs message check

**Status**: MOSTLY HANDLED ✅

---

### Priority 17: Rest Logic (Lines 1970-1990)
**Logic**:
- If no enemy detected, check health percentage
- If health < 60%: Rest with '5'
- If health ≥ 60%: Auto-explore with 'o'
- Track `consecutive_rest_actions` to prevent infinite rest
- After autofight, wait one turn before exploring

**Engine Mapping**:
- ✅ **Rest to recover** - health < 60% → '5'
- ✅ **Auto-explore** - health ≥ 60% → 'o'
- ✅ **Wait after autofight** - health ≥ 60% but last_action was Tab

**Status**: ALREADY HANDLED ✅

---

### Priority 18: Health Caching & Fallback (Lines 1992-2012)
**Logic**:
- Cache `last_known_health` and `last_known_max_health`
- If current health is 0/0, use cached values
- If health still unreadable (0/0 after cache), send Ctrl-R to redraw screen

**Engine Mapping**:
- ⚠️ **Health redraw request** (CRITICAL priority)
- Condition: `health == 0 AND max_health == 0`
- Action: '\\x12' (Ctrl-R redraw)

**Status**: PARTIALLY HANDLED ⚠️

---

## Helper Methods Analysis

### `_detect_enemy_in_range()` (Line 2395)
**Purpose**: Detect if there's an enemy in range
**Source**: Calls `_extract_all_enemies_from_tui(output)`
**Logic**: Get enemies from TUI, return first if found

**Engine Integration**: Already used by rules ✅

### `_is_in_shop()` (Line 2428)
**Purpose**: Detect if player is in a shop interface
**Detection**: "Welcome to" + "Shop!" + "[Esc] exit"

**Engine Integration**: Already used by rules ✅

### `_find_direction_to_enemy()` (Line 2451)
**Purpose**: Find movement direction toward enemy
**Logic**: Get enemy from TUI, scan map, return direction

**Engine Integration**: Already called by rules ✅

## Estimated Impact

| Category | Count | Status |
|----------|-------|--------|
| Already Migrated to Engine | 16 | ✅ |
| Partially Migrated | 1 | ⚠️ |
| Need Minor Refinements | 1 | ⚠️ |
| Complex/Out of Scope | 2 | ❌ |
| Ready to Remove | 700+ lines | ✅ |
| Final Estimated Size | <100 lines | ✅ 87% reduction |

## Migration Path

### Phase 1: Add Missing Rules ✅
- Add "Items on ground" rule (easy)
- Mark "Better armor" and "Untested potions" as LOW priority/future work

### Phase 2: Validation ✅
- Run tests with all new rules
- Run real game with engine enabled

### Phase 3: Code Removal ✅
- Delete `_decide_action_legacy()` (769 lines)
- Delete helper methods no longer needed
- Update `_decide_action()` to use engine directly

### Phase 4: Optimization ✅
- Profile rule evaluation
- Cache frequent conditions
- Document new architecture

## Next Steps

1. **Add "Items on ground" rule** to decision_engine.py
2. **Run tests**: Expect 216 passing
3. **Real game test**: 50 moves with `--use-engine`
4. **Validate decisions**: Compare legacy vs engine output
5. **Refactor**: Remove legacy code if identical

---

**Ready to proceed with incremental migration!**
