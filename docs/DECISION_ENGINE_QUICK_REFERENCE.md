# DecisionEngine Quick Reference

## Quick Start

### Using the Engine

```python
from decision_engine import DecisionEngine, create_default_engine, Priority

# Create engine with default rules
engine = create_default_engine()

# Prepare context
context = bot._prepare_decision_context(output)

# Get decision
command, reason = engine.decide(context)
```

### Adding a Custom Rule

```python
from decision_engine import Rule, Priority, DecisionContext

rule = Rule(
    name="Heal on critical",
    priority=Priority.URGENT,
    condition=lambda ctx: ctx.health_percentage < 30,
    action=lambda ctx: ('q', "Critical heal needed")
)

engine.add_rule(rule)
```

### Testing a Rule

```python
def test_my_rule():
    engine = DecisionEngine()
    engine.add_rule(my_custom_rule)
    
    ctx = DecisionContext(
        output="", health=20, max_health=100, level=1, dungeon_level=1,
        enemy_detected=True, enemy_name="orc",
        # ... other fields with default values
    )
    
    command, reason = engine.decide(ctx)
    assert command == 'q'
```

---

## Rule Template

```python
Rule(
    name="descriptive_name",                                    # What this rule does
    priority=Priority.NORMAL,                                   # When to evaluate (1-30)
    condition=lambda ctx: ctx.health < 50,                      # If this is true...
    action=lambda ctx: ('q', "Quaffing potion")                 # ...execute this action
)
```

---

## Priority Cheat Sheet

| Priority | Value | When | Examples |
|----------|-------|------|----------|
| CRITICAL | 1 | Immediate threats, menu prompts | Equip prompt, save game |
| URGENT | 5 | Level-up, damage recovery | Level-up handler, rest |
| HIGH | 10 | Combat decisions | Autofight, enemy detected |
| NORMAL | 20 | Standard gameplay | Explore, items |
| LOW | 30 | Fallbacks | Default action |

**Rule:** Lower priority value = evaluated first

---

## DecisionContext Fields

```python
# Game state
health: int                             # Current HP
max_health: int                         # Max HP
level: int                              # Experience level
dungeon_level: int                      # Current dungeon depth

# Detections
enemy_detected: bool                    # Enemy visible?
enemy_name: str                         # "goblin", "orc", etc.
items_on_ground: bool                   # Items to pick up?
in_shop: bool                           # In shop interface?
in_inventory_screen: bool               # Viewing inventory?
in_item_pickup_menu: bool               # Pick up menu?
in_menu: bool                           # Generic menu?

# Flags
equip_slot_pending: bool                # Waiting for equip slot?
quaff_slot_pending: bool                # Waiting for quaff slot?
has_level_up: bool                      # Level-up message?
has_more_prompt: bool                   # --more-- prompt?
attribute_increase_prompt: bool         # Stat increase prompt?
save_game_prompt: bool                  # Save game prompt?

# Previous state
last_action_sent: str                   # Last command sent
last_level_up_processed: int            # Level already handled
last_attribute_increase_level: int      # Stat increase level
last_equipment_check: int               # Equipment check move count
last_inventory_refresh: int             # Inventory refresh move count
move_count: int                         # Total moves taken

# Complex state
has_gameplay_indicators: bool           # Game is playable?
gameplay_started: bool                  # Started active gameplay?
goto_state: Optional[str]               # Descending level state
goto_target_level: int                  # Target level for descent

# Computed property
@property
def health_percentage(self) -> float:   # (health / max_health) * 100
```

---

## Common Patterns

### Check Health

```python
# In condition:
lambda ctx: ctx.health_percentage >= 60  # Good health
lambda ctx: ctx.health_percentage < 30   # Critical

# In action:
lambda ctx: ('o', f"Explore (health: {ctx.health_percentage:.1f}%)")
```

### Detect Enemy

```python
# In condition:
lambda ctx: ctx.enemy_detected and ctx.health_percentage > 70

# In action:
lambda ctx: ('\t', f"Autofight {ctx.enemy_name}")
```

### Check Prompt

```python
# In condition:
lambda ctx: ctx.has_more_prompt
lambda ctx: ctx.attribute_increase_prompt and ctx.level > ctx.last_attribute_increase_level

# In action:
lambda ctx: (' ', "Dismiss prompt")
lambda ctx: ('S', "Choose strength")
```

### Level-based Logic

```python
# In condition:
lambda ctx: ctx.level > ctx.last_level_up_processed  # New level!

# In action:
lambda ctx: (' ', f"Level {ctx.level}!")
```

---

## Default Engine Rules

| Rule | Priority | Condition | Action |
|------|----------|-----------|--------|
| Equip slot | CRITICAL | `equip_slot_pending` | Return slot letter |
| Quaff slot | CRITICAL | `quaff_slot_pending` | Return slot letter |
| Attribute increase | CRITICAL | prompt + new level | 'S' (Strength) |
| Save game prompt | CRITICAL | `save_game_prompt` | 'n' (No) |
| More prompt | CRITICAL | `has_more_prompt` | ' ' (Space) |
| Shop detected | HIGH | `in_shop` | '\x1b' (Escape) |
| Inventory screen | HIGH | `in_inventory_screen` | Handle + exit |
| Menu state | HIGH | `in_menu` | '.' (Wait) |
| Level-up | URGENT | `has_level_up` + new level | ' ' or '.' |
| Items on ground | URGENT | `items_on_ground` | 'g' (Grab) |
| Combat low health | NORMAL | enemy + health ≤ 70% | Movement |
| Combat normal health | NORMAL | enemy + health > 70% | '\t' (Autofight) |
| Explore good health | NORMAL | health ≥ 60% | 'o' (Explore) |
| Rest low health | NORMAL | health < 60% | '5' (Rest) |
| Goto location type | NORMAL | `goto_state == 'awaiting_location_type'` | 'D' (Dungeon) |
| Goto level number | NORMAL | `goto_state == 'awaiting_level_number'` | Level # |

---

## Integration with bot.py

### Initialization
```python
# In DCSSBot.__init__()
self.decision_engine = create_default_engine()
```

### State Preparation
```python
def _prepare_decision_context(self, output: str) -> DecisionContext:
    """Extract all game state into context object."""
    # ... parse output, detect situations, return DecisionContext
```

### Usage in _decide_action (Future)
```python
def _decide_action(self, output: str) -> Optional[str]:
    context = self._prepare_decision_context(output)
    command, reason = self.decision_engine.decide(context)
    if command is not None:
        return self._return_action(command, reason)
    # ... legacy fallback
```

---

## Testing Example

### Unit Test

```python
def test_combat_low_health_movement():
    """Verify combat uses movement when health is low."""
    engine = create_default_engine()
    
    ctx = DecisionContext(
        output="", health=40, max_health=100, level=1, dungeon_level=1,
        enemy_detected=True, enemy_name="bat",
        # ... other required fields
    )
    
    command, reason = engine.decide(ctx)
    assert "low health" in reason.lower()
```

### Integration Test

```python
def test_full_combat_sequence():
    """Test: Detect enemy → Autofight → Rest → Explore."""
    engine = create_default_engine()
    bot = DCSSBot()
    
    # Enemy detected, health good
    ctx1 = DecisionContext(..., enemy_detected=True, health=80, max_health=100)
    cmd1, _ = engine.decide(ctx1)
    assert cmd1 == '\t'  # Autofight
    
    # After combat, need healing
    ctx2 = DecisionContext(..., enemy_detected=False, health=30, max_health=100)
    cmd2, _ = engine.decide(ctx2)
    assert cmd2 == '5'  # Rest
    
    # Recovered, explore
    ctx3 = DecisionContext(..., enemy_detected=False, health=75, max_health=100)
    cmd3, _ = engine.decide(ctx3)
    assert cmd3 == 'o'  # Explore
```

---

## Performance Notes

- **Context creation**: O(1) - direct assignments
- **Rule evaluation**: O(n) where n = number of rules (~20)
- **Per-move overhead**: <1ms (negligible)
- **Memory**: ~2KB total (engine + rules + context)

---

## Common Mistakes to Avoid

### ❌ DON'T

```python
# Missing other required fields
ctx = DecisionContext(health=50, max_health=100)  # Missing 28+ fields!

# Returning wrong tuple type
action = lambda ctx: 'q'  # Should return (command, reason)

# Condition that can throw exception
condition = lambda ctx: ctx.enemy_name.upper()  # May throw if not detected

# Modifying context in action
action = lambda ctx: (ctx.health := 0, "died")  # Context is read-only!
```

### ✅ DO

```python
# Provide all required fields
ctx = DecisionContext(
    output="", health=50, max_health=100, level=1, dungeon_level=1,
    enemy_detected=False, enemy_name="", items_on_ground=False,
    # ... all 30+ fields
)

# Return (command, reason) tuple
action = lambda ctx: ('q', "Quaffing potion")

# Safe condition with default handling
condition = lambda ctx: ctx.enemy_detected and ctx.health_percentage > 50

# Use context properties, don't modify
action = lambda ctx: ('o', f"Health: {ctx.health_percentage:.1f}%")
```

---

## Documentation

- **Technical Guide**: `DECISION_ENGINE_IMPLEMENTATION.md`
- **Executive Summary**: `DECISION_ENGINE_SUMMARY.md`
- **Test Examples**: `tests/test_decision_engine.py`
- **Source Code**: `decision_engine.py` (well-commented)

---

## Need Help?

1. **Usage Questions**: See `DECISION_ENGINE_IMPLEMENTATION.md` "Usage Examples" section
2. **Test Examples**: Check `tests/test_decision_engine.py`
3. **Architecture**: Read "Architecture Innovation" section of `DECISION_ENGINE_SUMMARY.md`
4. **Code**: `decision_engine.py` has detailed docstrings

---

**Version**: 1.0  
**Status**: Phase 3a Complete - Ready for Migration  
**Last Updated**: January 31, 2026
