# Equipment System Documentation

## Overview

The DCSS Bot includes a comprehensive equipment management system that automatically detects and equips better armor to improve the player character's Armor Class (AC). In DCSS, lower AC values represent better protection.

## Key Concepts

### Armor Class (AC)

In DCSS, Armor Class (AC) is a defensive stat where **lower values are better**:
- AC = 10 is typical unarmored AC
- AC = 5 means 5 points of protection (good armor)
- AC = 0 means excellent protection (plate mail + accessories)
- AC values can go negative with heavy armor

The bot tracks AC values internally as:
- **Positive protection (+X)** in DCSS displays (e.g., "+2 leather armour") converts to **negative AC value (-2)** in the bot
- Example: "+5 chain mail" = AC -5 (5 points of protection)

### Equipment Slots

DCSS armor can be equipped in these slots:
- **body**: Robes, armor, tunics, scale mail (main protection)
- **head**: Helmets, crowns, circlets
- **hands**: Gloves, gauntlets
- **feet**: Boots, sandals
- **neck**: Rings, amulets, necklaces (accessories)

## Architecture

### Data Flow

```
[Game Screen] → [GameStateParser] → [parse_inventory_screen()]
                                    ↓
                            [InventoryItem] (ac_value, equipment_slot)
                                    ↓
                            [GameState.equipped_items]
                                    ↓
                            [DCSSBot._find_and_equip_better_armor()]
                                    ↓
                            [Send 'e' command + slot letter]
```

### Core Components

#### 1. InventoryItem Dataclass

Located in `game_state.py` lines 16-27:

```python
@dataclass
class InventoryItem:
    slot: str                          # 'a', 'b', 'c', etc.
    name: str                          # Item name
    quantity: int = 1
    identified: bool = True
    color: Optional[str] = None
    item_type: str = "unknown"         # "armor", "weapon", "potion", etc.
    ac_value: int = 0                  # AC value (lower = better)
    is_equipped: bool = False          # Currently equipped?
    equipment_slot: Optional[str] = None  # "body", "head", "hands", "feet", "neck"
```

#### 2. AC Value Parsing

In `game_state.py` lines 393-402, when parsing inventory:

```python
# Extract AC value from armor items (e.g., "+2 leather armour" → ac_value = -2)
if item_type == "armor":
    ac_match = re.search(r'([+-])(\d+)', item_desc)
    if ac_match:
        sign = ac_match.group(1)
        value = int(ac_match.group(2))
        # +X protection = -X AC value (better)
        ac_value = -value if sign == '+' else value
```

#### 3. Equipment Slot Detection

In `game_state.py` lines 404-418, based on item keywords:

```python
desc_lower = item_desc.lower()
if any(b in desc_lower for b in ['robe', 'armour', 'armor', 'tunic', 'leather', 'scale']):
    equipment_slot = 'body'
elif any(g in desc_lower for g in ['gloves', 'gauntlets', 'hands']):
    equipment_slot = 'hands'
elif any(f in desc_lower for f in ['boots', 'feet', 'sandals']):
    equipment_slot = 'feet'
elif any(h in desc_lower for h in ['helmet', 'helm', 'circlet', 'head', 'crown']):
    equipment_slot = 'head'
elif any(n in desc_lower for n in ['ring', 'amulet', 'necklace', 'neck']):
    equipment_slot = 'neck'
```

#### 4. Finding Better Armor

In `game_state.py` lines 494-540, the `GameStateParser.find_better_armor()` method:

```python
def find_better_armor(self) -> Optional[Tuple[str, InventoryItem]]:
    """
    Find armor items in inventory that are better than currently equipped.
    Returns better armor based on AC value (lower AC is better).
    Only considers armor items that can be equipped.
    """
```

**Algorithm**:
1. Iterate through all inventory items
2. Skip non-armor items and already-equipped items
3. For each armor item:
   - Find currently equipped item in same slot
   - If no equipped item, add to candidates (improve empty slot)
   - If equipped item exists, check if new item has better (lower) AC value
4. Sort candidates by improvement magnitude (most improvement first)
5. Return best candidate or None

#### 5. Equipment Detection in Decision Logic

In `bot.py` lines 1420-1425, during decision loop:

```python
# CHECK FOR BETTER ARMOR/EQUIPMENT - EQUIP TO IMPROVE AC
if self.move_count > self.last_equipment_check + 10:
    self.last_equipment_check = self.move_count
    equip_action = self._find_and_equip_better_armor()
    if equip_action:
        return equip_action
```

**Timing**: Only checks every 10 moves to avoid wasting time on repeated comparisons.

#### 6. Equipment Execution

In `bot.py` lines 1116-1140, `_find_and_equip_better_armor()`:

```python
def _find_and_equip_better_armor(self) -> Optional[str]:
    better_armor = self.parser.find_better_armor()
    
    if not better_armor:
        return None
    
    slot, item = better_armor
    
    # Only equip if significant improvement
    if item.ac_value < -2:  # At least +2 protection
        logger.info(f"🛡️ Found better armor: {item.name} (AC {item.ac_value})")
        self.equip_slot = slot  # Store for next step
        return self._return_action('e', f"Equipping better armor: {item.name}")
    
    return None
```

#### 7. Equipment Prompt Response

In `bot.py` lines 1321-1324, handling the equip prompt:

```python
# CHECK FOR EQUIP SLOT PROMPT - SEND SLOT LETTER AFTER 'e' COMMAND
if self.equip_slot:
    logger.info(f"🛡️ Responding to equip prompt with slot '{self.equip_slot}'")
    slot = self.equip_slot
    self.equip_slot = None  # Clear for next time
    return self._return_action(slot, f"Equipping armor from slot {slot}")
```

**Two-step process**:
1. Send 'e' command → Bot stores slot in `self.equip_slot`
2. Next turn, game prompts "Equip which item?"
3. Send slot letter → Equipment is equipped

## Supported Armor Types

### Body Armor
- Leather armour (+0 to +2)
- Scale mail (+2 to +4)
- Chain mail (+4 to +6)
- Plate mail (+8 to +10)
- Robes (typically +1 to +3)

### Headgear
- Helmets (+1 to +2)
- Circlets (+0 to +1)
- Crowns (+1 to +2)

### Handwear
- Gloves (+0 to +1)
- Gauntlets (+1 to +2)

### Footwear
- Boots (+0 to +1)
- Sandals (+0)

### Accessories (Neck Slot)
- Rings of protection (+1 to +3)
- Amulets (various effects)
- Necklaces (+0 to +1)

## State Tracking

### GameState Fields (game_state.py lines 56-58)

```python
# Equipment tracking
equipped_items: Dict[str, InventoryItem] = field(default_factory=dict)  # equipment_slot → InventoryItem
current_ac: int = 10  # Current armor class (lower is better, default ~10)
```

### Bot State Variables (bot.py lines 150-151)

```python
self.equip_slot = None  # Current slot being equipped (set by _find_and_equip_better_armor)
self.last_equipment_check = 0  # Move count when we last checked for equipment upgrades
```

## Example Scenarios

### Scenario 1: Finding Better Body Armor

```
Initial State:
  - Equipped: a +1 leather armour (AC -1)
  - Inventory: b +3 chain mail (AC -3)

Detection:
  - find_better_armor() compares:
    - Slot: 'body'
    - Current: AC -1
    - Available: AC -3
    - Improvement: -1 - (-3) = 2 points

Action:
  1. Send 'e' command
  2. Game prompts: "Equip which item? (a-z)"
  3. Send 'b' (slot of chain mail)
  4. Result: Player now equipped with +3 chain mail (AC -3)
```

### Scenario 2: Filling Empty Slot

```
Initial State:
  - Equipped: a +2 leather armour (body)
  - Inventory: b +1 helmet (head - empty slot)

Detection:
  - find_better_armor() finds:
    - Head slot is empty
    - Item b (+1 helmet) can fill it
    - Improvement: equipping from empty slot

Action:
  1. Send 'e' command
  2. Send 'b' (helmet slot)
  3. Result: Player now has helmet equipped
```

### Scenario 3: No Improvement Found

```
Initial State:
  - Equipped: a +5 plate mail (AC -5) - excellent armor
  - Inventory: b +2 chain mail (AC -2)

Detection:
  - find_better_armor() checks:
    - Body slot: AC -2 is worse than -5
    - No improvement available
  - Returns None

Action:
  - No equip action taken
  - Bot continues with other decisions
```

## Implementation Details

### AC Calculation

Total AC from all equipped items:

```python
def get_equipped_ac_total(self) -> int:
    """Calculate total AC from all equipped armor items."""
    total_ac = 0
    for item in self.state.equipped_items.values():
        total_ac += item.ac_value
    return total_ac
```

Example:
- +2 leather armour (body) = AC -2
- +1 helmet (head) = AC -1
- +1 boots (feet) = AC -1
- **Total AC = -4** (4 points of protection)

### Comparison Logic

When comparing armor for the same slot:
1. Lower (more negative) AC value = better protection
2. Find maximum improvement (most negative difference)
3. Only equip if significant improvement (at least +2 or empty slot)

### Avoiding Infinite Loops

- Equipment check happens only every 10 moves
- Once equipped item is marked `is_equipped=True`, it won't be checked again
- After sending equip command, slot is cleared and next action waits for game response

## Testing

Comprehensive test suite in `tests/test_equipment_system.py` (22 tests):

### Test Categories

1. **AC Value Parsing** (5 tests)
   - Positive AC (protection)
   - Negative AC (penalty)
   - Zero AC
   - High protection
   - Rings with AC

2. **Equipment Slot Detection** (6 tests)
   - Body armor detection
   - Hand armor detection
   - Foot armor detection
   - Head armor detection
   - Neck jewelry detection

3. **Equipment Tracking** (4 tests)
   - GameState initialization
   - Marking items as equipped
   - Total AC calculation (single/multiple items)

4. **Finding Better Armor** (5 tests)
   - Finding better armor in inventory
   - Skipping already-equipped items
   - Filling empty slots
   - No improvement scenarios
   - Multiple slots comparison

5. **Comparison Logic** (2 tests)
   - Significance threshold
   - Slot independence

All 138 tests pass ✓

## Future Enhancements

1. **Cursed Item Detection**: Detect and avoid cursed armor
2. **Special Properties**: Track enchantments (e.g., "ring of cold resistance")
3. **Encumbrance Tracking**: Avoid heavy armor that slows movement
4. **Stat Requirements**: Consider character stats when equipping
5. **Material Properties**: Track material (leather vs metal) for special effects
6. **Automatic Identification**: Use quaff system to identify unknown armor properties
7. **Swap Strategy**: Option to swap items mid-combat if tactical advantage found

## Related Components

- **Inventory System**: `game_state.py` inventory parsing
- **Decision Logic**: `bot.py` `_decide_action()` method
- **Item Pickup**: `bot.py` `_grab_items()` method
- **Activity Logging**: `bot_unified_display.py` activity panel
- **Potion System**: Similar two-step process for quaffing potions

## Debugging

Enable debug logging:

```bash
python main.py --steps 100 --debug
```

Look for equipment-related log entries:
- `🛡️ Found better armor:` - Equipment upgrade detected
- `🛡️ Responding to equip prompt` - Sending slot letter
- Check `logs/screens_*/` for visual equipment changes

## References

- DCSS Armor Class: https://crawl.develz.org/wiki/display/0.28/Armor
- DCSS Equipment: https://crawl.develz.org/wiki/display/0.28/Equipment
- Code: [game_state.py](game_state.py#L494-L540), [bot.py](bot.py#L1116-L1140)
