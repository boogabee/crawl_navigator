# Unified TUI Display - Visual Example

## What You'll See When Running the Bot

### Example 1: During Startup

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    CRAWL GAME OUTPUT (Top Section)                         ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Please enter your name: ➖                                               ║
║                                                                            ║
║  Choices:                                                                  ║
║    a - Dungeon Crawl Stone Soup                                           ║
║                                                                            ║
║  Enter your choice: ↵                                                      ║
║                                                                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║ [Move 0000] | HP 0/0 | Mana 0/0                                           ║
╠════════════════════════════════════════════════════════════════════════════╣
║ BOT ACTIVITY (Last 5 messages)                                             ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║ [14:23:15] ✓ Startup menu detected                                        ║
║ [14:23:17] ℹ Sending character name: Ranger042                           ║
║ [14:23:18] ℹ Selecting 'Dungeon Crawl' from menu                         ║
║ [14:23:20] ✓ Gameplay started!                                            ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

### Example 2: During Gameplay

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    CRAWL GAME OUTPUT (Top Section)                         ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Dungeon Crawl Stone Soup version 0.28.0 (tiles)                         ║
║  ────────────────────────────────────────────────────                    ║
║  Elven Ranger                                                              ║
║  Depth 1 of Dungeon                                                        ║
║                                                                            ║
║  @  Level 1 Ranger                                                         ║
║  HP 20/20 | Mana 5/5 | AC 6 | EV 13 | Str 15 Int 11 Wis 12 Dex 16        ║
║                                                                            ║
║  A simple room with walls                                                 ║
║  .......#####                                                              ║
║  .@....#.....                                                              ║
║  .......#####                                                              ║
║  ...........#                                                              ║
║                                                                            ║
║  ---- Turn 47 ----                                                         ║
║                                                                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║ [Move 0047] Moving | HP 20/20 | Mana 5/5 | Level 1 | Depth Dungeon:1    ║
╠════════════════════════════════════════════════════════════════════════════╣
║ BOT ACTIVITY (Last 12 messages)                                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║ [14:23:20] ✓ Gameplay started!                                            ║
║ [14:23:21] ℹ Moved north                                                  ║
║ [14:23:22] ℹ Moved east                                                   ║
║ [14:23:23] ℹ Moved east                                                   ║
║ [14:23:24] ⚠ Detected goblin (hostile) at (8, 5)                         ║
║ [14:23:25] ℹ Moved south (away from threat)                              ║
║ [14:23:26] ℹ Moved south                                                  ║
║ [14:23:27] ℹ Found dagger (+1, +2)                                       ║
║ [14:23:27] ✓ Picked up dagger                                             ║
║ [14:23:28] ℹ Moved east                                                   ║
║ [14:23:29] ℹ Moved east                                                   ║
║ [14:23:30] ⚙ Screen updated: 1250 bytes                                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

### Example 3: When Enemy Detected

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    CRAWL GAME OUTPUT (Top Section)                         ║
╠════════════════════════════════════════════════════════════════════════════╣
║  @  Level 2 Ranger                                                         ║
║  HP 18/25 | Mana 7/8 | AC 6 | EV 13                                       ║
║                                                                            ║
║  A spore fungus          g - goblin (friendly) (asleep)                   ║
║  .......#####            G - goblin (hostile)                              ║
║  .@G...#.....                                                              ║
║  .......#####                                                              ║
║  ...........#                                                              ║
║                                                                            ║
║  ---- Turn 103 ----                                                        ║
║                                                                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║ [Move 0103] Combat | HP 18/25 | Mana 7/8 | Level 2 | Depth Dungeon:1    ║
╠════════════════════════════════════════════════════════════════════════════╣
║ BOT ACTIVITY (Last 12 messages)                                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║ [14:24:45] ℹ Moved south                                                  ║
║ [14:24:46] ℹ Moved east                                                   ║
║ [14:24:47] ✓ Level up! Now level 2                                        ║
║ [14:24:48] ℹ Moved east                                                   ║
║ [14:24:49] ⚠ DANGER: Hostile goblin detected at (2, 1)                   ║
║ [14:24:50] ℹ Health: 18/25 (72%)                                          ║
║ [14:24:51] ℹ Evaluated combat vs escape: COMBAT RECOMMENDED               ║
║ [14:24:52] ℹ Attacking goblin with dagger                                 ║
║ [14:24:52] ✓ HIT! Goblin takes 4 damage                                   ║
║ [14:24:53] ⚠ Goblin counterattacks! Takes 3 damage                        ║
║ [14:24:54] ℹ Health now: 15/25 (60%)                                      ║
║ [14:24:55] ℹ Attacking again...                                           ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Color Scheme

### Message Types (with ANSI colors)

```
✓ Success Messages (Green - Color 32)
  Example: [14:23:20] ✓ Gameplay started!
  Example: [14:24:47] ✓ Level up! Now level 2
  Example: [14:24:52] ✓ HIT! Goblin takes 4 damage

ℹ Info Messages (Default - No color)
  Example: [14:23:21] ℹ Moved north
  Example: [14:24:48] ℹ Health: 18/25 (72%)

⚙ Debug Messages (Cyan - Color 36)
  Example: [14:23:30] ⚙ Screen updated: 1250 bytes
  Example: [14:25:01] ⚙ Parser state: GAMEPLAY

⚠ Warning Messages (Yellow - Color 33)
  Example: [14:23:24] ⚠ Detected goblin (hostile) at (8, 5)
  Example: [14:24:49] ⚠ DANGER: Hostile goblin detected
  Example: [14:24:53] ⚠ Goblin counterattacks!

✗ Error Messages (Red - Color 31)
  Example: [14:25:15] ✗ Failed to move: blocked
  Example: [14:25:20] ✗ Screen parse error
```

## Activity Panel Behavior

### Automatic Updates
- Updates every time `_log_activity()` is called
- Shows last 12 lines of activity
- Oldest messages scroll off the top
- Full history (100 messages) kept in memory

### Always Visible
- Present during entire bot execution
- Visible during character creation
- Visible during gameplay
- Can show setup/configuration messages during startup

### Disabled When
- Bot is not running
- Terminal is too small (< 30 lines)
- ANSI color support not available (falls back to plain text)

## Impact on User Experience

### Before (Old Display)
- Only game screen visible
- Activity logged to file or terminal separately
- Hard to correlate game events with bot actions
- Missed context when scrolling

### After (Unified Display) ✓
- Game screen + bot activity in one view
- Real-time visibility of what bot is doing
- Clear cause-and-effect relationship
- No missed context
- Easier debugging
- More engaging to watch

## Customization

Users can customize the display by modifying `bot_unified_display.py`:

```python
# Change panel height (line 19)
ACTIVITY_PANEL_HEIGHT = 15  # Show 15 lines instead of 12

# Change max history (line 42 in bot initialization)
self.unified_display = UnifiedBotDisplay(max_messages=200)  # Keep 200 messages

# Add custom activity logging anywhere in bot.py
self._log_activity("Custom event occurred", "warning")
```

## Integration Ready

The unified display is **fully integrated** and **ready to use**:

1. ✓ Module created: `bot_unified_display.py` (227 lines)
2. ✓ Integration complete: `bot.py` updated with imports and initialization
3. ✓ Display method: `_display_tui_to_user()` rewritten to use unified display
4. ✓ Activity logging: `_log_activity()` method added
5. ✓ Startup logging: Initial events logged during character creation
6. ✓ Tests passing: All 11 existing tests still pass

**Just run the bot normally** - the unified display will appear automatically!

```bash
python main.py --steps 10
```

