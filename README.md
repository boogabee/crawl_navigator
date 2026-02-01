# DCSS Bot

An automated bot for playing Dungeon Crawl Stone Soup using a local installation.

## Features

✅ **Local Execution** - Runs Crawl as a subprocess with PTY support
✅ **Startup Automation** - Handles menus and character creation automatically
✅ **Unified Display** - Shows Crawl TUI with integrated 12-line activity panel
✅ **Activity Logging** - Timestamped, color-coded bot actions and events in real-time
✅ **TUI-Based Threat Detection** - Detects enemies from game display (not unreliable message stream)
✅ **Item Pickup System** - Automatically collects gold and items from defeated enemies
✅ **Inventory Tracking** - Parses and tracks inventory items with type detection
✅ **Equipment System** - Automatically equips better armor to improve AC (Armor Class)
✅ **Potion Identification** - Identifies unknown potions by quaffing (game-session specific)
✅ **Action Recording** - Records all moves and game states to files
✅ **Game Loop** - Executes gameplay with configurable step limits and debug logging

## Current Implementation

The bot is **fully functional** and successfully:
- Starts local Crawl instance with cbreak mode PTY (character-by-character input with echo)
- Navigates startup menus automatically: name entry → auto-advance to character creation → menu selection
- Handles character creation: species/class/background selection with automatic progression
  - Captures screenshot of each character creation menu (species, class, background, skills)
- Plays the game by sending movement/action commands
- **Item Pickup & Inventory** (v0.3.0): 
  - Detects items on ground ("You see here", "Things that are here:")
  - Sends 'g' command to grab items automatically
  - Collects gold for future resource management
  - Parses inventory screen ('i' command) to track items
- **Equipment System** (v1.6): Automatic armor optimization
  - Parses AC values from armor items (e.g., "+2 leather armour" → AC -2)
  - Detects equipment slots (body, head, hands, feet, neck)
  - Compares inventory armor against equipped items
  - Automatically sends 'e' command to equip better armor
  - Responds to equip prompts with correct slot letters
  - Tracks all equipped items and calculates total AC protection
  - See [EQUIPMENT_SYSTEM.md](EQUIPMENT_SYSTEM.md) for detailed documentation
- **Potion Identification** (v0.3.0):
  - Identifies unknown potions by quaffing them
  - Detects potion effect from game messages
  - Maintains color-to-effect mapping for current game session
  - Respects DCSS design: effects change per game, mapping is session-specific
- **TUI-Based Decisions** (v1.3): Detects threats, items, and game state from TUI display (not message stream)
  - Enemy detection parses monsters section from TUI
  - Health/status tracked from TUI status line
  - All decisions based on what the display shows NOW
- Displays unified interface: game TUI + activity panel in single view
- Logs all bot actions with timestamps and severity levels
- Uses reliable timeout-based I/O with proper terminal emulation mode for stable gameplay
- Gameplay loop runs without crashes and properly captures all screens


## Installation

1. Clone or extract this project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Credentials are pre-configured in `credentials.py`:
   - Game: Account `boogabee` / `stonesoup`

## Usage

Run the bot:
```bash
python main.py
```

Options:
```bash
# Run for a specific number of steps
python main.py --steps 100

# Enable debug logging to see detailed execution info
python main.py --debug

# Run for 50 steps with debug output
python main.py --steps 50 --debug
```

## Logging System

The bot automatically creates detailed session logs in the `logs/` directory with the format:
```
logs/bot_session_YYYYMMDD_HHMMSS.log
```

Each log file contains:
- **Session Header**: Timestamp, server, player info
- **Move Entries**: Timestamped records with format:
  ```
  [HH:MM:SS.mmm] Move #N
  Action: [Command sent or action taken]
  ────────────────────────────────────
  SCREEN: [Full ANSI-formatted game board and state]
  ```

Example log excerpt:
```
=== DCSS Bot Session Log ===
Started: 2026-01-22 05:46:20
Server: crawl.develz.org:22
Player: crawl

[05:46:20.024] Move #0
Action: Game Started - Initial State
────────────────────────────────────
SCREEN: [game board display]

[05:46:21.156] Move #1
Action: Sending '.'
────────────────────────────────────
SCREEN: [updated game board]
```

These logs allow you to:
- Replay and analyze each move the bot made
- See the exact game state at each decision point
- Debug bot behavior by reviewing screen captures
- Keep a permanent record of bot sessions

### Viewing Raw Logs with ANSI Formatting

For detailed debugging, raw screen captures are saved alongside cleaned versions in the `logs/screens_YYYYMMDD_HHMMSS/` directory with full ANSI color codes and formatting intact.

To view raw logs with ANSI formatting preserved in the terminal:
```bash
# Option 1: View with vim terminal
vim logs/screens_20260123_160829/0007_raw.txt
# Then in vim, run: :term cat %

# Option 2: View directly with cat
cat logs/screens_20260123_160829/0007_raw.txt

# Option 3: Use less with support for raw output
less -R logs/screens_20260123_160829/0007_raw.txt
```

The `:term cat %` vim command is particularly useful because it preserves full ANSI formatting including colors and cursor positioning, allowing you to see exactly how the game output appeared on the remote terminal.

## Architecture

### Core Files

- **`main.py`** - Entry point with CLI argument parsing
- **`bot.py`** - Main bot class with:
  - Game loop execution and step management
  - Local process and character creation menu handling
  - Action decision logic
  - Unified display and activity logging
  - Game state tracking
- **`local_client.py`** - PTY connection handler:
  - Pseudo-terminal management with cbreak mode (character-by-character with echo)
  - Reliable read/write operations with select() and non-blocking I/O
  - Process management and signal handling
  - Proper terminal mode configuration for ncurses applications
- **`bot_unified_display.py`** - Unified display engine:
  - Combines game TUI with 12-line activity panel
  - Color-coded activity messages with timestamps
  - Terminal-aware formatting and sizing
- **`game_state.py`** - Game state parser:
  - Detects game readiness (looks for `@`, `HP:`, `AC:` in output)
  - Detects game-over conditions
  - Parses character position and status
- **`credentials.py`** - Configuration with game and display settings

### Data Flow

```
main.py
    ↓
bot.run(max_steps)
    ├→ _local_startup() - Handle PTY setup and character creation
    │  ├→ Create PTY via LocalCrawlClient
    │  ├→ Send character name (logs: "Sending character name: [name]")
    │  ├→ Select menu (logs: "Selecting 'Dungeon Crawl'...")
    │  └→ Detect gameplay (logs: "Gameplay started!")
    └→ Game Loop (per step):
       ├→ Read output with 2.0s timeout (fixed: now respects full duration ✅)
       ├→ Parse game state with pyte
       ├→ _decide_action() - Choose next move
       ├→ Send command via PTY
       ├→ Read response with 2.0s timeout
       ├→ Log activity to unified display (if action significant)
       └→ Display unified interface (game screen + activity panel)
```

## Extending the Bot

### Improving Decision Making

Edit the `_decide_action()` method in `bot.py` to implement smarter strategies:
- Use pathfinding algorithms for navigation
- Identify and avoid dangerous monsters
- Implement inventory management based on character class
- Track explored areas and adapt exploration patterns
- Manage hunger and rest

### Parsing More State

Enhance `game_state.py` to parse additional information:
- Monster positions and types visible on screen
- Item locations and quality
- Status conditions (poisoned, confused, etc.)
- Spell and ability information
- Dungeon features (stairs, altars, shops)

### Adding New Commands

Common DCSS commands:
- Movement: `h`, `j`, `k`, `l`, `y`, `u`, `b`, `n` (vi-style)
- `o`: Auto-explore
- `g`: Grab/pickup items
- `i`: Inventory
- `d`: Drop item
- `.`: Wait one turn
- `>`, `<`: Use stairs (down/up)
- `e`: Examine items
- `a`: Use ability/spell

## Popular DCSS Servers

- crawl.project39.net (Main server)
- underhound.eu (EU server)
- termcast.develz.org (Development server)

## Notes

- The bot's performance depends on your DCSS strategies
- Start with simple exploration and gradually add more complex behaviors
- Monitor logs to understand what the bot is doing
- The game is turn-based, so the bot can safely wait for output between actions
- DCSS has permadeath, so test your strategies carefully
- Consider creating a dedicated account for the bot on public servers

## License

MIT
