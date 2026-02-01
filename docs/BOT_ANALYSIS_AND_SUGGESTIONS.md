# DCSS Bot Analysis & Progression Suggestions

## Summary of Three Test Runs

### Run Results
- **Run 1 (30 steps)**: Level 1 → Level 1 (33% progress), Health 16/18, Location: Dungeon:1
- **Run 2 (30 steps)**: Level 1 → Level 2 (50% progress), Health 24/24, Location: Dungeon:2
- **Run 3 (100 steps)**: Level 1 → Level 2 (5% progress), Health 24/24, Location: Unknown (started in Dungeon:1)

### Key Observations

1. **Gold Collection**: Across all runs, gold collected = 0
   - Items are encountered (adders, bats, lizards killed) but NO gold is picked up
   - No items collected from corpses or ground
   - This severely limits buying from shops or acquiring better equipment

2. **Dungeon Progression**: Slow
   - Run 2 managed to descend from Dungeon:1 to Dungeon:2
   - But Run 3 (100 steps) achieved less progress despite 3-4x more steps
   - Auto-explore works but doesn't efficiently complete levels

3. **Combat Performance**: Decent
   - Bot successfully engages enemies (frilled lizard, adder, bat, ball python, quokka)
   - Uses autofight effectively with Tab key
   - Health management after combat works (waiting to recover)

4. **Experience Gain**: Moderate but inconsistent
   - Run 2 gained a full level in 30 steps
   - Run 3 gained only 5% progress in 100 steps
   - Level-up detection and prompt handling works correctly

5. **No Logged Events**: "Unique Enemies Encountered: 0" / "Total Events: 0"
   - Event tracking may not be working properly
   - Significant game interactions not being recorded

---

## Critical Issues Preventing Progression

### 1. **No Gold/Item Pickup** (HIGHEST PRIORITY)
**Problem**: Bot kills enemies and finds items but never collects them
- Corpses lying around are not auto-picked up
- Gold pieces not collected
- Prevents acquiring better equipment or potions
- No ability to buy from shops even if visiting them

**Why It Matters**:
- DCSS requires gold for equipment upgrades via shops
- Better equipment (armor, weapons) dramatically improves combat capability
- Resistances from equipment prevent status effects
- Speed equipment allows faster exploration

**Solution Approach**:
- Add item pickup detection (after combat, check message log for "Items that are here:")
- Detect items on ground via TUI display parsing
- Send 'g' command to grab items, ',' to autopickup, or navigate to items and use 'p'
- Parse inventory after pickup to track equipment changes

### 2. **Auto-Explore Inefficiency** (HIGH PRIORITY)
**Problem**: Auto-explore ('o' command) is very slow and doesn't complete levels efficiently
- Sometimes gets stuck on unreachable areas
- Takes excessive moves to explore each level
- Doesn't handle obstacles like locked doors

**Why It Matters**:
- More moves = more time = opportunity for unexpected deaths
- Inefficient exploration wastes the step budget on redundant areas
- Doesn't descend to harder levels where better experience gain occurs

**Solution Approach**:
- Track when exploration gets stuck (repeated movements in same area)
- Use 'g' (goto) command to descend after exploration completes
- Add logic to detect staircase locations and navigate to them
- Alternative: Implement smarter movement (manual pathfinding to stairs)

### 3. **No Shop Usage** (MEDIUM PRIORITY)
**Problem**: Bot exits shops without buying anything
- Has 0 gold anyway (due to issue #1)
- Shops are now auto-detected and exited, but should eventually buy items
- No logic to track useful equipment and plan purchases

**Why It Matters**:
- Shops offer significant equipment upgrades
- Strategic purchases early in game dramatically improve survivability
- Gold becomes a valuable resource once collection is implemented

**Solution Approach**:
- Once gold pickup works, implement shop evaluation logic
- Parse shop inventory and identify useful items
- Calculate gold efficiency (price vs. benefit)
- Buy prioritized items: resistances > armor upgrades > weapons
- Track equipment slots (amulet, ring, body armor, boots, gloves)

### 4. **Weapon Upgrade Inefficiency** (MEDIUM PRIORITY)
**Problem**: Bot uses starting war axe entire run
- No detection of better weapons found during exploration
- Equips forced gear correctly but doesn't seek upgrades
- Early game weapon upgrades significantly boost combat efficiency

**Why It Matters**:
- Better weapons = faster enemy dispatch
- Faster kills = less damage taken
- Current weapon does minimal damage (hits but "do no damage" messages)

**Solution Approach**:
- Parse equipment found in "Things that are here:" messages
- Detect weapon drops (especially polearms, axes, swords)
- Parse inventory to find unequipped weapons
- Send 'e' to equip better weapons when found
- Add simple damage calculation (weapon type + enchantment level)

### 5. **Potion/Scroll Usage** (MEDIUM PRIORITY)
**Problem**: No detection or usage of potions/scrolls found
- Healing potions never used despite combat damage taken
- Scrolls of teleportation or identify not utilized
- Status effect potions (cure poison) not used

**Why It Matters**:
- Healing potions critical for survivability (restore health without delay)
- Teleportation can escape dangerous situations
- ID scrolls for unidentified equipment

**Solution Approach**:
- Parse inventory to track potions/scrolls
- Detect when health drops below threshold (50%) and health potions available
- Send 'q' to quaff potions by slot (q then 'a', 'b', etc.)
- Reserve some potions for emergencies only

### 6. **Limited Threat Assessment** (MEDIUM PRIORITY)
**Problem**: Bot doesn't consider enemy threat level when deciding to fight
- Fights any detected enemy regardless of danger
- No distinction between "easy" (weak lizard) vs "dangerous" (orc warrior) enemies
- No retreat/escape logic when outmatched

**Why It Matters**:
- Some early-game enemies are highly dangerous (centaurs, ogres)
- Death is instant game-over with no recovery
- Smart threat assessment prevents preventable deaths

**Solution Approach**:
- Create enemy danger database (threat level by creature type)
- Parse enemy health / status effects before committing to autofight
- Implement "run away" logic for dangerous enemies (not implemented yet)
- Use stairs to escape if surrounded

### 7. **No Ability/Magic Usage** (LOW PRIORITY)
**Problem**: Bot doesn't cast spells or use abilities
- Likely has mana but never uses spells
- Wands/staffs found but not used
- Special abilities (evoke) not triggered

**Why It Matters**:
- Magic provides additional combat power
- Some enemies have weaknesses to specific spells
- Wands can provide utility (teleportation, healing, lightning)

**Solution Approach**:
- Parse mana from character panel (Magic: X/Y)
- Detect spells known (from 'a' abilities list)
- Evaluate when to cast vs. melee
- For now: only use offensive spells on dangerous enemies

### 8. **No Dungeon Strategy** (LOW PRIORITY)
**Problem**: Bot descends indiscriminately and doesn't track branch decisions
- Always descends to next floor
- No tracking of which branch is better
- No awareness of danger level vs. current capability

**Why It Matters**:
- Dungeon depths 1-2 are safer for leveling
- Some branches (Orcish Mines) have powerful enemies early
- Smart descending maximizes experience gain with minimal risk

**Solution Approach**:
- For now: keep exploring Dungeon:1 until level 3-4
- Then descend when high health and leveled
- Track depth progression

---

## Recommended Implementation Priority

### Immediate (Blocks all progression):
1. **Item Pickup System** - Without this, no gold or better equipment
2. **Inventory Tracking** - Know what the bot has

### Short-term (Major improvements):
3. **Weapon Detection & Equipment Swap** - Dramatically improves combat
4. **Health Potion Usage** - Survivability
5. **Threat Assessment** - Prevents unnecessary deaths

### Medium-term (Nice-to-have):
6. **Shop Integration** - Buy needed resistances and upgrades
7. **Better Exploration** - More efficient level clearing
8. **Ability/Spell System** - Additional combat options

### Long-term (Advanced):
9. **Dungeon Strategy** - Branch awareness and optimal progression
10. **Advanced Threat Handling** - Enemy weaknesses, resistances matching

---

## Code Changes Required

### 1. Item Pickup (HIGH IMPACT)
```
Location: bot.py _decide_action() method
Add check after combat:
- Parse message log for "Things that are here:"
- Extract item names and positions
- Send 'g' to grab, or move + ',' to autopickup
- Track items in inventory

Example: After bat/lizard killed
"Things that are here:"
"a -2 stones"
→ Move to item location and grab
```

### 2. Inventory Parsing (HIGH IMPACT)
```
Location: bot.py or game_state.py
Create _parse_inventory() method:
- Send 'i' to view inventory
- Parse each slot (a) sword, b) ring, etc.
- Store in bot state for later reference
- Track gold amount from inventory display

This unblocks: Weapon selection, potion usage, shop buying
```

### 3. Threat Detection (MEDIUM IMPACT)
```
Location: bot.py _detect_enemy_in_range()
Add threat level system:
- Define enemy_danger = {'zombie': 1, 'bat': 2, 'centaur': 8}
- Check enemy health from combat log (not visible in TUI)
- Return (detected: bool, enemy_name: str, threat_level: int)
- Use in _decide_action to decide fight vs. flee

Current: fights all enemies
After: only fights enemies below threat threshold
```

### 4. Potion Usage (MEDIUM IMPACT)
```
Location: bot.py _decide_action() method
Add health recovery logic:
- Check current health
- If health < 50% and healing potions available
- Send 'q' + potion slot letter to quaff
- Wait for recovery before resuming

Prevents death from accumulated damage
```

### 5. Equipment Upgrade (MEDIUM IMPACT)
```
Location: bot.py or game_state.py
After combat:
- Parse "Found X" messages
- Check if item is better than equipped
- Send 'e' (equip) command
- Select new equipment from inventory

Weapon priority: Polearms > Axes > Swords > Maces
Armor priority: Robe > Leather > Nothing
```

---

## Testing Strategy

After each change:
1. Run bot for 30 steps
2. Check gold collected (should > 0)
3. Check equipment (should upgrade)
4. Check inventory (should have items)
5. Verify no crashes or unexpected behavior
6. Run 3x to ensure consistency

Target progression after all changes:
- 30 steps: Level 2-3, Gold > 50, Equipment upgraded
- 100 steps: Level 4-5, Gold > 200, Multiple equipment upgrades
- 300 steps: Level 6-7, Dungeon:3-4, Better combat effectiveness

---

## Summary

The bot is **functionally working** but **not progressing effectively** because:

1. **Missing Gold/Item Economy** - Cannot acquire better equipment
2. **Inefficient Combat Power** - No weapon upgrades, no health recovery
3. **No Resource Management** - Doesn't track or use potions
4. **Limited Strategy** - No threat assessment or planning

Implementing item pickup and inventory management would be a **game-changer** for progression. These two systems unlock the entire equipment economy and make the game actually playable for extended runs.

All issues are solvable with the existing infrastructure (TUI parsing, message log, etc.). The bot has good bones—it just needs resource management.
