# Item Pickup and Inventory Tracking System

## Overview

This document describes the newly implemented item pickup and inventory tracking system for the DCSS bot. This system enables the bot to:

1. **Detect items on the ground** after combat or exploration
2. **Grab items** using the 'g' command
3. **Track inventory** by parsing the inventory screen ('i' command)
4. **Identify potions** by quaffing untested potions (potions with unknown effects)
5. **Maintain a mapping** of potion colors to their effects for the current game session

## Architecture

### Data Structures

#### InventoryItem (game_state.py)
```python
@dataclass
class InventoryItem:
    slot: str              # 'a', 'b', 'c', etc.
    name: str              # Full item name
    quantity: int          # Number of items in this slot (default 1)
    identified: bool       # Whether we know what this item is
    color: Optional[str]   # Color for unidentified potions
    item_type: str         # 'weapon', 'armor', 'potion', 'scroll', 'gold', etc.
```

#### GameState Enhancements (game_state.py)
```python
@dataclass
class GameState:
    # ... existing fields ...
    
    # New inventory tracking fields:
    inventory_items: Dict[str, InventoryItem]  # slot -> InventoryItem
    identified_potions: Dict[str, str]         # color -> effect (e.g., "purple" -> "healing")
    untested_potions: Dict[str, str]           # slot -> color (e.g., "a" -> "purple")
    items_on_ground: List[Tuple[str, int]]     # (item_name, quantity)
```

### Parsing Methods

#### GameStateParser.parse_inventory_screen(screen_text: str) -> Dict[str, InventoryItem]

Parses the inventory screen (displayed after pressing 'i' command) and extracts all items.

**Features:**
- Handles identified items: "a - a purple potion of healing"
- Handles unidentified items: "b - a red potion (unknown)"
- Extracts potion colors (purple, red, blue, green, cyan, magenta, etc.)
- Detects item types: weapon, armor, potion, scroll, gold
- Tracks unidentified potions for later quaffing
- Handles ANSI color codes in the screen text

**Example:**
```python
parser = GameStateParser()
screen = """
a - a +0 war axe
b - a purple potion of healing
c - a red potion (unknown)
d - 42 gold pieces
"""
items = parser.parse_inventory_screen(screen)
# items['c'].color == 'red'
# items['c'].identified == False
# parser.state.untested_potions == {'c': 'red'}
```

#### GameStateParser.parse_ground_items(screen_text: str) -> List[Tuple[str, int]]

Parses ground items from message log. Handles multiple formats:
- "You see here 10 gold pieces."
- "You see here a purple potion."
- "Things that are here: a - gold piece, b - potion"

### Bot Decision Logic

The bot integrates item pickup and potion management into the decision loop with this priority:

1. **Quaff slot selection** - If waiting for potion selection after 'q' command
2. **Attribute increase** - Respond to level-up attribute prompts
3. **Save game rejection** - Reject accidental save prompts
4. **Level-up processing** - Handle level-up messages
5. **--more-- prompts** - Dismiss paging prompts
6. **Shop detection** - Exit shops
7. **Item pickup** ← NEW: Grab items from ground (detecting "Things that are here")
8. **Potion identification** ← NEW: Quaff unidentified potions when safe
9. **Inventory refresh** ← NEW: Parse inventory screen when viewing
10. **Combat/exploration** - Original gameplay logic

### Helper Methods (bot.py)

#### _detect_items_on_ground(output: str) -> bool
Returns True if the output contains item indicators like "you see here", "things that are here", "gold pieces", "potion", etc.

#### _grab_items() -> Optional[str]
Sends the 'g' command to grab items from the ground.

#### _identify_untested_potions() -> Optional[str]
Sends the 'q' command to quaff an untested potion, starting the identification process.

#### _refresh_inventory() -> Optional[str]
Sends the 'i' command to open the inventory screen for parsing.

#### _check_and_handle_inventory_state(output: str) -> Optional[str]
Detects if we're in the inventory screen, parses it, and exits with Escape.

#### _parse_potion_effect_from_message(output: str) -> Optional[Tuple[str, str]]
Parses the effect message after a potion is quaffed (e.g., "You feel healed" → healing).

## Potion Identification System

### How It Works

1. **First Encounter**: When an unidentified potion is found (e.g., "a red potion (unknown)")
   - Color is recorded: `untested_potions['a'] = 'red'`
   - Item is marked: `item.identified = False`

2. **Quaffing Decision**: When safe (not in combat, health > 50%)
   - Bot sends 'q' command to start quaffing
   - Game prompts: "Quaff which item? (a-z)"
   - Bot responds with the slot letter

3. **Effect Detection**: After quaffing
   - Game displays effect message (e.g., "You feel much better")
   - Bot parses message to determine effect
   - Mapping is created: `identified_potions['red'] = 'healing'`

4. **Future Encounters**: When the same color is found again
   - Bot knows the effect immediately
   - Can use potions strategically (e.g., save red healing potions for emergencies)

### Session-Specific Mapping

**Important**: Potion colors and effects change from game to game in DCSS. The mapping is maintained only for the current game session:
- `identified_potions` dict tracks known effects during the game
- On game exit, this mapping is not persisted
- Each new game starts fresh with no known potion effects

This matches real DCSS gameplay where the player must re-identify potions in each game.

## Decision Logic Integration

### State Variables

```python
class DCSSBot:
    quaff_slot = None           # Current slot being quaffed
    last_items_on_ground_check = 0  # Move count for items check
    inventory_stale = True      # Cache validity flag
    last_inventory_refresh = 0  # Move count for last refresh
    in_inventory_screen = False # Currently viewing inventory
```

### Priority Order in _decide_action()

```python
if quaff_slot_waiting:
    # Respond with slot letter
    return quaff_slot_response

if items_detected_on_ground():
    # Grab items
    return grab_command

if untested_potions and not_in_combat and health_good:
    # Quaff to identify
    return quaff_command

if in_inventory_screen:
    # Parse and exit
    return exit_inventory
```

## Examples

### Example 1: Finding and Grabbing Items

```
Move 15: Enemy defeated
  → Output contains: "You see here 10 gold pieces."
  → Bot detects items
  → Bot sends 'g' command
  → Move 16: Parses "You picked up 10 gold pieces"
  → Gold counter increases
```

### Example 2: Identifying an Unknown Potion

```
Move 20: Inventory contains:
  - a - +0 war axe
  - b - a purple potion (unknown)

Move 21-22: Bot waits (checking for safe time)
  → Health > 60%, not in combat
  
Move 23: Bot sends 'q' command
  → Game asks: "Quaff which item? (a-z)"
  
Move 24: Bot sends 'b' (the potion slot)
  → Game displays: "You feel much better."
  
Move 25+: Bot now knows:
  → Purple potions heal
  → `identified_potions['purple'] = 'healing'`
  → Next purple potion can be used strategically
```

### Example 3: Complex Inventory Parsing

```
Inventory screen shows:
a - a +1 war axe
b - a ring of fire resistance
c - a blue potion of haste
d - a green potion (unknown)
e - a yellow potion (unknown)
f - a scroll of identify
g - 150 gold pieces

Parsed as:
- items['a'].type = 'weapon'
- items['b'].type = 'armor'
- items['c'].type = 'potion', identified=True
- items['d'].type = 'potion', identified=False, color='green'
- items['e'].type = 'potion', identified=False, color='yellow'
- items['f'].type = 'scroll'
- items['g'].type = 'gold', quantity=150

Tracking:
- identified_potions = {} (or previous games' mappings)
- untested_potions = {'d': 'green', 'e': 'yellow'}
```

## Testing

### Test Coverage

The system includes 35 comprehensive tests covering:

1. **Inventory Parsing** (7 tests)
   - Empty inventory
   - Simple items
   - Identified vs. unidentified potions
   - Multiple potions mixed
   - Scrolls
   - ANSI codes

2. **Ground Items Parsing** (4 tests)
   - Single items
   - Multiple items
   - "Things that are here:" format
   - No items scenario

3. **Item Dataclass** (3 tests)
   - Item creation
   - Potion items
   - Gold items

4. **Game State Tracking** (2 tests)
   - Inventory fields present
   - Initial state validation

5. **Potion Colors** (18 parametrized tests)
   - All supported colors: purple, red, blue, green, yellow, cyan, magenta, brown, gray, white, black, orange, golden, silver, pink, violet, indigo, turquoise

6. **Complex Scenarios** (1 test)
   - Full inventory with all item types

**Total: 116 tests passing** (81 original + 35 new)

## Known Limitations

1. **Item Pickup on Ground**: The 'g' command grabs items, but in some cases where the player isn't adjacent, the grab may fail silently. Future enhancement: detect "you need to move closer" message and move to items first.

2. **Potion Effect Inference**: Currently uses simple message keywords. Some potion effects are nuanced and may not be reliably detected from messages. Future enhancement: use behavior observation (e.g., health increase) to confirm effect.

3. **Inventory Auto-Refresh**: Currently inventory is parsed when 'i' command is sent, but the bot doesn't periodically refresh. Future enhancement: add scheduled inventory refreshes to detect items picked up during exploration.

4. **Slot Persistence**: Inventory slots shift as items are used/dropped. The bot doesn't track slot changes. Future enhancement: maintain item identity across slot changes.

## Future Enhancements

1. **Smart Potion Usage**
   - Use healing potions when health drops below 50%
   - Save rare potions for emergencies
   - Use resistance potions preemptively

2. **Equipment Swapping**
   - Detect better weapons/armor
   - Equip upgrades automatically
   - Track equipped vs. inventory items

3. **Shop Integration**
   - Use picked-up gold to buy items from shops
   - Identify which items are worth buying
   - Strategic purchase planning

4. **Spell/Ability System**
   - Track learned spells
   - Use offensive spells on dangerous enemies
   - Manage mana wisely

5. **Gold Management**
   - Track gold spent vs. earned
   - Identify cost-benefit of purchases
   - Plan shopping routes

## Implementation Details

### Files Modified

1. **game_state.py**
   - Added `InventoryItem` dataclass
   - Enhanced `GameState` with inventory tracking fields
   - Added `parse_inventory_screen()` method
   - Added `parse_ground_items()` method

2. **bot.py**
   - Added import for `Tuple` type
   - Added inventory tracking state variables
   - Added `_detect_items_on_ground()` method
   - Added `_grab_items()` method
   - Added `_identify_untested_potions()` method
   - Added `_refresh_inventory()` method
   - Added `_check_and_handle_inventory_state()` method
   - Added `_parse_potion_effect_from_message()` method
   - Integrated into `_decide_action()` decision logic
   - Added quaff slot handling

3. **tests/test_inventory_and_potions.py** (NEW)
   - 35 comprehensive tests for inventory system
   - Tests for parsing, tracking, and complex scenarios

### Backward Compatibility

All changes are backward compatible:
- Existing game state parsing unaffected
- New inventory fields are optional
- Existing decision logic unchanged
- All 81 original tests still pass

## Usage

The item pickup and inventory system runs automatically as part of the bot's decision loop. No additional configuration is needed.

```bash
# Run bot with inventory and item tracking enabled (default)
python3 main.py --steps 100

# Check logs for inventory parsing
# Look for "📦 Items detected on ground" 
# Look for "🔮 Found untested X potion"
```

## Debugging

Enable debug logging to see inventory operations:

```bash
python3 main.py --steps 30 --debug

# Will show:
# [DEBUG] Currently in inventory screen
# [DEBUG] Parsed inventory: 5 items
# [DEBUG] a: +0 war axe (type=weapon, identified=True)
# etc.
```
