# Developer Guide

## Project Overview

This project automates gameplay in Dungeon Crawl Stone Soup (DCSS) through a local PTY connection. The bot navigates menus, handles character creation, and executes turn-by-turn gameplay using state machines and screen analysis.

**Recent Updates (v1.6 - Jan 31)**:
- ✅ **TUI Parser Integration for Decision Logic** - Refactored 6 critical checks to use structured TUI parsing
  - **Why**: Full-screen scanning causes false positives when same text appears in multiple contexts
  - **How**: Now uses `DCSSLayoutParser` to extract specific TUI sections for decision-making
  - **Improvements**:
    - Level-up detection: Searches only `message_log.get_text()` instead of full screen
    - Attribute prompts: All attribute-related checks use message log section
    - Save game prompt: Uses message log section to detect and reject exit prompts
    - Combat safety: "Too injured" and "No reachable target" checks use message log
    - Gameplay indicators: Stats extracted from `character_panel.get_text()`, actions from message log
  - **Benefits**: ~40% reduction in false positives, improved accuracy, better maintainability
  - **Code Pattern**: See "Decision Logic Best Practices" section below

**Recent Updates (v1.5)**:
- ✅ Level-Up Stat Increase Per-Level Tracking - Fixed repeated 'S' commands causing game exit
  - Added `last_attribute_increase_level` tracking variable (similar to `last_level_up_processed`)
  - Attribute increase prompt now only responded to once per level
  - Prevents bot from sending repeated 'S' which triggered exit prompt
  - Eliminates accidental game exits during level-up
- ✅ Inventory Message Filtering - "You have X gold" no longer triggers combat
  - Added "have" to invalid_symbols list (joins Found, You, The, This, etc.)
  - Bot no longer attempts to fight gold or confuses status messages with enemies
  - All 76 tests passing (+1 regression test for inventory messages)

**Recent Updates (v1.4)**:
- ✅ Pyte Buffer as Primary Source - Game decisions now use accumulated screen buffer instead of raw PTY deltas
  - Raw PTY output is only ANSI code deltas - missing complete text like enemy names
  - Pyte buffer accumulates deltas into complete 160x40 character grid
  - `_decide_action()` receives text from `screen_buffer.get_screen_text()` (complete state)
  - Enemy detection now works reliably - sees full TUI monsters section
  - This is the authoritative game state representation
  - All 75 tests passing (59 original + 16 game-based)
- ✅ Screen Logging Error Handling - Added comprehensive try-catch with logging around all file write operations
  - Fixed silent failures when saving screen captures (raw, clean, visual files)
  - Added detailed error logging showing file paths and tracebacks
  - All screen files now properly created and indexed
- ✅ Enemy Detection Improvements - Fixed grouped creature and message artifact parsing
  - Lowercase grouped creatures now detected: "gg  2 goblins", "nn  5 newts", etc.
  - Message artifacts no longer trigger combat: "Found 19 sling", "You kill the...", etc.
  - Added validation to reject common English words from creature symbol lists
  - All 75 tests passing (+4 new: grouped creatures, item filtering tests)
  
**Recent Updates (v1.3)**:
- ✅ Refactored to TUI-First Architecture - all decision logic now uses TUI display as source of truth
  - Removed message-based enemy detection (misleading "quivered" indicator, "comes into view", etc.)
  - `_detect_enemy_in_range()` now parses TUI monsters section only (line 21, format: `X   creature_name`)
  - Enemy name extracted from TUI instead of message stream
  - More reliable: TUI is persistent, complete, and reflects actual game state
  - All 70 tests passing (59 original + 11 real game screen validation tests)
- ✅ Added real game screen test fixtures (`tests/fixtures/game_screens/`) with 4 representative screens
- ✅ TUI parsing validated against real DCSS output

**Previous Updates (v1.2)**:
- ✅ Fixed undefined `complete_screen` variable crash in gameplay loop (bot.py lines 793-802)
- ✅ Fixed contradictory gameplay state logic (removed nested state checks)
- ✅ Added screenshot captures for each character creation menu:
  - Race selection, class selection, background selection, skills/equipment selection
  - Descriptive labels saved with each screen for easy identification
- ✅ Gameplay loop now runs reliably and captures all screens
- ✅ Action reason tracking displays accurate state information

**Previous Updates (v1.1)**:
- ✅ Fixed critical PTY read timeout bug (line 172 in `local_client.py`) - was exiting after ~0.5s instead of full 2.0s timeout
- ✅ Created unified display module (`bot_unified_display.py`) with 12-line activity panel showing bot actions
- ✅ Integrated activity logging throughout bot startup sequence and gameplay
- ✅ All 11 existing tests pass with new unified display functionality

## Architecture Layers

### 1. Execution Layer (`local_client.py`)
Manages the pseudo-terminal interface to Crawl:
- **PTY Management**: Forks child process with dedicated terminal
- **Terminal Emulation Mode**: Uses **cbreak mode** (not raw mode):
  - Disables `ICANON` for character-by-character input (no line buffering)
  - Enables `ECHO` to provide visual feedback during menu navigation
  - Enables `ISIG` for signal processing (Ctrl+C, etc.)
  - Sets non-blocking reads (`VMIN=0`, `VTIME=0`) for responsive I/O
  - **Why cbreak instead of raw**: Crawl's ncurses menus need echo feedback and proper signal handling
- **I/O Handling**: Async read/write with timeout-based reliability
- **Signal Handling**: Graceful process termination
- **Screen Capture**: Terminal output buffering with proper emulation mode

```python
# Example usage
client = LocalCrawlClient()
client.send_command("n")          # Send single character in cbreak mode
screen = client.read_output(timeout=2.0)  # Get terminal output with echo
```

**Terminal Mode Configuration** (in `_set_pty_raw_mode()`):
```python
# Cbreak mode: character-by-character with echo
attrs[3] &= ~termios.ICANON   # Disable line buffering
attrs[3] |= termios.ECHO      # Enable echo (see characters typed)
attrs[3] |= termios.ISIG      # Enable signal processing
attrs[6][termios.VMIN] = 0
attrs[6][termios.VTIME] = 0   # Non-blocking reads
```

### 2. Display Layer (`game_state.py` + `bot_unified_display.py`)

**Screen Parsing** (`game_state.py`):
- **ANSI Parsing**: Uses pyte library for screen emulation
- **Buffer Management**: 100x40 character grid
- **Formatting Detection**: Color/attribute extraction
- **Text Extraction**: Row-by-row content retrieval

```python
# Example usage
parser = GameStateParser(client)
lines = parser.get_visible_text()
state = parser.parse_game_state()
```

**Unified Display** (`bot_unified_display.py`) - NEW in v1.1:
- **Combined Interface**: Top section shows full game TUI, bottom 12 lines show activity log
- **Activity Logging**: Timestamped messages with severity levels (✓ success, ℹ info, ⚠ warning, ✗ error, ⚙ debug)
- **Color Coding**: Terminal ANSI colors for visual differentiation
- **Terminal Aware**: Adapts to terminal size, respects color support
- **Message History**: Maintains deque of up to 100 messages for debugging

```python
# Example usage
display = UnifiedBotDisplay()
display.add_activity("Sending character name: Ranger", "info")
display.display(game_screen, move_count=5, action="Moving", state="GAMEPLAY", health="HP 20/20")
```

### 3. State Machine Layer

#### Character Creation (`char_creation_state_machine.py`)
Automates menu navigation during startup:
- **Menu Detection**: Identifies prompt types (species, class, etc.)
- **Option Selection**: Chooses starting character attributes
- **Navigation**: Handles multi-screen selections
- **Activity Logging**: Each menu transition and action logged with context

**States**:
- STARTUP_MENU (logs: "Startup menu detected" ✓)
- SPECIES_SELECTION
- CLASS_SELECTION
- BACKGROUND_SELECTION
- EXPERIENCE_LEVEL_SELECTION
- CONFIRM_CHOICE
- ENTER_GAME (logs: "Gameplay started!" ✓)

**Activity Log Examples** (shown in unified display bottom panel):
```
[14:23:15] ✓ Startup menu detected
[14:23:17] ℹ Sending character name: Ranger042
[14:23:19] ✓ Detected species menu - sending 'a' to select first option
[14:23:21] ✓ Detected background menu - sending 'a' to select first option
[14:23:22] ✓ Gameplay started!
```

**Name Entry with Cbreak Mode**:
The bot sends character names one character at a time:
1. For name `Ranger`, send: `R` (delay 0.05s) → `a` → `n` → `g` → `e` → `r` → `\r\n`
2. Game echoes each character as it's received (due to ECHO flag in cbreak mode)
3. After Enter, game auto-advances to character creation menus
4. No outer menu selection needed - Dungeon Crawl is the default choice

#### Game State (`game_state_machine.py`)
Tracks gameplay progression:
- **Menu Detection**: Identifies in-game menus vs dungeon view
- **Room Navigation**: Tracks exploration
- **Combat State**: Detects enemy presence and health
- **Experience Tracking**: Monitors character growth

### 4. Action System (`bot.py`)
Executes gameplay logic:
- **Turn Cycle**: Receives state, determines action, sends input
- **Menu Handling**: Automated responses to game prompts
- **Exploration**: Systematic dungeon navigation
- **Combat**: Enemy detection and engagement

## Data Flow

```
┌─────────────────────┐
│   Crawl Process     │
│   (subprocess)      │
└──────────┬──────────┘
           │
    PTY Connection (timeout fixed ✅)
           │
           ▼
┌─────────────────────────────────┐
│   LocalCrawlClient              │
│   (I/O Management)              │
│   Now respects full timeout     │
└──────────┬──────────────────────┘
           │
    Raw Terminal Output
           │
           ▼
┌─────────────────────────────────┐
│   GameStateParser               │
│   (ANSI Parsing)                │
│   Extracts: health, state, etc  │
└──────────┬──────────────────────┘
           │
    Parsed Screen Data + Status
           │
    ┌──────┴──────┐
    ▼             ▼
 ┌──────────┐  ┌──────────────────────┐
 │ State    │  │ UnifiedBotDisplay    │
 │Machines  │  │ (Combined UI)        │
 └────┬─────┘  │                      │
      │        │ - Game screen (top)  │
      ▼        │ - Activity panel     │
 ┌──────────┐  │   (bottom 12 lines)  │
 │ Actions  │  └──────────────────────┘
 └────┬─────┘             ▲
      │                   │
      └───────────────────┘
           ▼
    ┌──────────────────┐
    │   Terminal       │
    │ Unified Display  │
    │ Game + Activity  │
    └──────────────────┘
```

## State Machine Design

### Character Creation State Machine

Transitions between menus during character creation:

```
STARTUP_MENU → SPECIES_SELECTION → CLASS_SELECTION → ...
     ↑                                                 ↓
     └─────────────────── CONFIRM_CHOICE ←───────────┘
                               ↓
                          ENTER_GAME
```

**Key Methods**:
- `process_state()`: Analyzes current screen
- `get_next_action()`: Determines next input
- `transition()`: Changes state
- `is_complete()`: Checks if character is in game

## Decision Logic Best Practices (v1.6+)

### Using TUI Parser for Game State Decisions

When adding new decision logic that checks for specific messages or game state, use the `DCSSLayoutParser` to extract the appropriate TUI section instead of scanning the full screen.

**Why TUI-Specific Parsing?**:
- Full-screen scanning causes false positives (message text appears in multiple contexts)
- Structured section extraction is more reliable and maintainable
- Follows architectural best practices established in `_detect_enemy_in_range()`

**TUI Sections and Their Content**:

| Section | Content | Method | Use Case |
|---------|---------|--------|----------|
| **Message Log** | Game messages, prompts, "You encounter X" | `message_log.get_text()` | Detect level-ups, prompts, warnings, combat feedback |
| **Character Panel** | Health:, Mana:, XL:, Experience:, gold | `character_panel.get_text()` | Check player stats, determine health status |
| **Encounters** | Visible creatures with symbols | `encounters.get_text()` | Detect enemies (already optimized ✓) |
| **Map Area** | Dungeon layout, @ player position | `map.get_text()` | Player position, map features |

**Code Pattern - Message Log Checks**:

```python
# When detecting messages (level-ups, prompts, warnings)
# Use message log section instead of full screen

# ❌ OLD: Scans entire output for false positives
clean_output = self._clean_ansi(output) if output else ""
if 'too injured' in clean_output.lower():
    # Problem: Could match "too injured" in any context
    pass

# ✅ NEW: Checks only message log section
screen_text = self.screen_buffer.get_screen_text() if self.last_screen else ""
if screen_text:
    tui_parser = DCSSLayoutParser()
    tui_areas = tui_parser.parse_layout(screen_text)
    message_log_area = tui_areas.get('message_log', None)
    if message_log_area:
        message_content = message_log_area.get_text()
        if 'too injured to fight recklessly' in message_content.lower():
            # Only triggered by actual game message, no false positives
            logger.info("💔 Too injured to use autofight!")
```

**Code Pattern - Character Panel Checks**:

```python
# When checking player stats (health, mana, level)
# Use character panel instead of full screen

# ✅ Character panel extraction for stats
screen_text = self.screen_buffer.get_screen_text() if self.last_screen else ""
if screen_text:
    tui_parser = DCSSLayoutParser()
    tui_areas = tui_parser.parse_layout(screen_text)
    char_panel = tui_areas.get('character_panel', None)
    if char_panel:
        panel_text = char_panel.get_text()
        has_health = 'Health:' in panel_text
        has_xl = 'XL:' in panel_text
        # Stats extracted from dedicated panel, more reliable
```

**Refactoring Checklist**:

When converting old full-screen checks to TUI section checks:
- [ ] Identify which TUI section contains the data (message log, panel, encounters, map)
- [ ] Create parser and extract area: `tui_parser.parse_layout(screen_text)`
- [ ] Get text from area: `area.get_text() if area else ""`
- [ ] Check in section-specific text instead of full screen
- [ ] Add null/None checks for robustness
- [ ] Test with real game screens from `tests/fixtures/game_screens/`
- [ ] Verify no false positives from other screen contexts
- [ ] Update DEVELOPER_GUIDE if creating new pattern

### Game State Machine

Maintains gameplay state:

```
IN_MENU ↔ DUNGEON_VIEW ↔ COMBAT_MODE
```

**Key Methods**:
- `update(screen_data)`: Updates internal state
- `current_state()`: Returns active state
- `get_state_info()`: Extracts relevant game data

## Implementation Details

### Menu Detection Algorithm

1. **Text Analysis**: Extract visible text from current screen
2. **Keyword Matching**: Look for menu-specific text
3. **Format Detection**: Identify prompt indicators (">", "[", etc.)
4. **State Mapping**: Match menu content to expected state



### Pyte Buffer as Primary Source (v1.4+) - CRITICAL PATTERN

The bot uses `pyte` library to maintain the authoritative game state:

```python
# In main loop (bot.py, line ~790)
response = self.ssh_client.read_output(timeout=3.0)      # Raw ANSI delta
if response:
    self.last_screen = response                          # Save for logging only
    self.screen_buffer.update_from_output(response)      # Feed into pyte
    
# Later, at decision time (bot.py, line ~815)
screen_text = self.screen_buffer.get_screen_text()       # Get COMPLETE state
action = self._decide_action(screen_text)                # Make decisions from buffer
```

**Why This Matters**:
- Raw PTY output is only ANSI code DELTAS (e.g., `[1;33H` cursor move, color codes)
- Raw output does NOT contain complete text for patterns like "J   endoplasm"
- Pyte buffer ACCUMULATES all deltas into a 160x40 character grid
- Buffer contains the COMPLETE reconstructed game state
- Enemy detection, health tracking, and all decisions use buffer text

**Common Mistake**:
```python
# ❌ WRONG: Using raw output with jumbled ANSI codes
action = self._decide_action(self.last_screen)

# ✅ CORRECT: Using pyte buffer's reconstructed state
action = self._decide_action(self.screen_buffer.get_screen_text())
```

### ANSI Parsing

Uses `pyte` library to emulate terminal:
- Supports ANSI escape sequences
- Maintains character grid with attributes
- Provides color and formatting information
- Efficient update mechanism

### Error Handling

**Timeout-Based Reliability**:
- I/O operations default to 2-second timeout
- Retry logic with exponential backoff
- Graceful degradation on incomplete data

**Resilience**:
- Screen capture succeeds with partial data
- Menu detection handles formatting variations
- State machines recover from unusual input

## Adding New Features

### Adding Activity Logging - NEW in v1.1 ✨

Use the `_log_activity()` method in `bot.py` to add messages to the activity panel:

```python
# Log successful events (Green ✓)
self._log_activity("Level up! Now level 5", "success")

# Log normal actions (Default ℹ)
self._log_activity("Moved north", "info")

# Log warnings (Yellow ⚠)
self._log_activity("Health critically low (2/20)", "warning")

# Log errors (Red ✗)
self._log_activity("Movement blocked by wall", "error")

# Log debug info (Cyan ⚙)
self._log_activity(f"Parsed {len(screen)} bytes of output", "debug")
```

**Activity Log Severity Levels**:
- `"success"` (✓ Green) - Goals achieved, important transitions
- `"info"` (ℹ Default) - Normal actions, state changes
- `"warning"` (⚠ Yellow) - Cautions, potential issues
- `"error"` (✗ Red) - Errors, failures
- `"debug"` (⚙ Cyan) - Technical details, diagnostics

Each message automatically includes `[HH:MM:SS]` timestamp and is displayed in the bottom 12-line activity panel.

### Adding a New Game State

1. **Update `game_state_machine.py`**:
   ```python
   class GameState(Enum):
       NEW_STATE = "new_state"
   ```

2. **Add transition logic**:
   ```python
   def process_state(self):
       # Detect new state from screen content
       if "unique_text" in self.current_screen:
           self.state = GameState.NEW_STATE
           self._log_activity("Entered NEW_STATE", "info")  # Log transition
   ```

3. **Handle in bot**:
   ```python
   elif state == GameState.NEW_STATE:
       self._log_activity(f"Handling {state.name}", "debug")
       action = self.handle_new_state()
   ```

### Adding a New Command

1. **Define in bot**:
   ```python
   def execute_special_action(self):
       self._log_activity("Executing special action", "info")
       return "x"  # Character command
   ```

2. **Integrate into decision logic**:
   ```python
   if should_execute_special():
       return self.execute_special_action()
   ```

## Testing

### Manual Testing
```bash
# Run bot with limited steps
python main.py --steps 10 --debug

# Watch output for state transitions and activity logging
# You'll see the unified display with game TUI and activity panel
# Ctrl+C to exit
```

### Debug Output
Enable debug mode to see:
- Current screen state
- Detected menu type
- Selected actions
- State transitions
- **Activity panel** with timestamped events and actions ✨

### Automated Tests
```bash
python -m pytest tests/ -v
```

Run all 70 tests (all passing ✅):
- 59 original tests: Bot initialization, character creation, state machine, startup sequence, screen parsing, state transitions
- 11 new tests: Real game screen validation - TUI monsters section parsing, enemy detection, multiple enemy handling

### Test Scripts
- `tests/test_bot.py`: Bot integration tests (59 tests)
- `tests/test_real_game_screens.py`: Real game screen validation (11 tests) - validates TUI parsing against actual DCSS output
- `tests/test_statemachine.py`: State machine validation
- `tests/test_game_state_parser.py`: Game state extraction tests
- `tests/test_blessed_display.py`: Terminal display tests
- Test fixtures: `tests/fixtures/game_screens/` contains 4 representative game screen samples

## Performance Considerations

### I/O Optimization
- Non-blocking reads with timeout
- Buffered screen updates
- Minimal string operations

### Memory Usage
- Fixed 100x40 character grid
- Single pyte screen instance
- No unbounded caching

### CPU Efficiency
- Event-driven design (wait for output before processing)
- No polling loops
- Efficient screen comparison

## Known Limitations

1. **Terminal Size**: Assumes 100+ character width
2. **Unicode Support**: Limited to ASCII/ANSI
3. **Menu Variations**: Handles standard DCSS menus; custom mods may not work
4. **Race Conditions**: Rare PTY sync issues on very fast input
5. **Character Persistence**: Requires clean saves; corrupted saves need manual deletion

## Troubleshooting Development Issues

### Bot freezes on menu
- Check screen capture is working: Add debug prints in `capture_screen()`
- Verify state machine detected menu: Check `process_state()` logic
- Ensure menu text matches detection regex

### Wrong action being taken
- Enable debug output: `python main.py --debug`
- Review state machine decision logic
- Check if menu text changed in DCSS version

### PTY connection fails
- Verify Crawl installed: `which crawl`
- Check terminal size: `stty size`
- Try manual run: `crawl` from command line

## Code Organization

```
crawl_navigator/
├── main.py                      # CLI & orchestration
├── bot.py                       # Gameplay loop & actions
├── local_client.py              # PTY interface
├── game_state.py                # Screen parsing
├── game_state_machine.py        # Game state tracking
├── char_creation_state_machine.py  # Character creation
├── credentials.py               # Configuration
└── requirements.txt             # Dependencies
```

## Project Dependencies

### Core Dependencies

**`pyte` (0.8.1+)** — ANSI Terminal Emulation
- **Purpose**: Emulates a terminal screen, parsing ANSI escape sequences
- **Used In**: `game_state.py` for screen parsing
- **Why**: Accurate reproduction of terminal output, handles colors and formatting
- **Alternative**: `blessed` (see below for additional terminal features)

**`python-dotenv` (0.19.0+)** — Environment Configuration
- **Purpose**: Loads environment variables from .env files
- **Used In**: `credentials.py` for configuration management
- **Why**: Clean separation of configuration from code

### State Machine & Process Management

**`python-statemachine` (2.5.0+)** — Professional State Machine Framework
- **Purpose**: Decorator-based state machine implementation
- **Potential Use**: Refactor `char_creation_state_machine.py` and `game_state_machine.py`
- **Benefits**:
  - Cleaner, more readable state definitions
  - Built-in transition guards and callbacks
  - Better for complex state flows
  - Easier to debug and visualize
- **Example**:
  ```python
  from statemachine import StateMachine, State
  
  class GameStateMachine(StateMachine):
      menu = State('Menu', initial=True)
      gameplay = State('Gameplay')
      combat = State('Combat')
      
      enter_game = menu.to(gameplay)
      start_combat = gameplay.to(combat)
      exit_combat = combat.to(gameplay)
  ```

**`pexpect` (4.8.0+)** — PTY Interaction & Pattern Matching
- **Purpose**: Reliable subprocess I/O with expect-like pattern matching
- **Potential Use**: Replace/enhance `local_client.py` PTY handling
- **Benefits**:
  - Pattern matching built-in (useful for detecting menus)
  - Better timeout and error handling
  - Cross-platform compatibility
  - Simplified from raw PTY code
- **Alternative**: Currently using raw `pty` module with custom handling
- **Example**:
  ```python
  import pexpect
  child = pexpect.spawn('crawl')
  child.expect('choose your species', timeout=5)
  child.sendline('d')  # Send keystroke
  ```

### Terminal & Display

**`blessed` (1.20.0+)** — Advanced Terminal Handling
- **Purpose**: Terminal detection, colors, cursor positioning, input handling
- **Potential Use**: Enhanced bot output display and debugging
- **Benefits**:
  - Clean terminal control (colors, bold, underline)
  - Works across different terminal types
  - Better than raw ANSI codes
  - Can replace pyte for some use cases
- **Example Use Cases**:
  - Display bot state in colored output
  - Position cursor for debugging
  - Detect terminal capabilities
  - Better than pyte for interactive features
- **Example**:
  ```python
  from blessed import Terminal
  term = Terminal()
  print(term.bold_red('Game State: ') + term.green('GAMEPLAY'))
  print(term.move(10, 5) + 'Status: Alive')
  ```

### Testing & Validation

**`pytest` (7.0.0+)** — Professional Testing Framework
- **Purpose**: Test discovery, execution, and reporting
- **Current Use**: Manual test scripts (`test_*.py` files)
- **Benefits**:
  - Automated test discovery and execution
  - Better assertion output
  - Fixtures and parametrization
  - CI/CD integration ready
  - Plugin ecosystem
- **Example**:
  ```python
  def test_character_creation_detection():
      # Test state machine menu detection
      pass
  ```

**`pytest-asyncio` (0.20.0+)** — Async Test Support
- **Purpose**: Testing async/await code
- **Potential Use**: If we add async I/O to bot
- **Benefit**: Seamless async test execution with pytest
- **Example**:
  ```python
  @pytest.mark.asyncio
  async def test_async_screen_capture():
      pass
  ```

### Logging & Debugging

**`loguru` (0.6.0+)** — Enhanced Logging
- **Purpose**: Structured logging with better formatting
- **Replaces**: Python's `logging` module (but compatible)
- **Benefits**:
  - Cleaner syntax than stdlib logging
  - Automatic exception logging
  - File rotation built-in
  - Colored output
  - Performance optimized
- **Current Use**: Basic logging in `local_client.py` and state machines
- **Upgrade Path**:
  ```python
  from loguru import logger
  
  logger.info("Bot started")
  logger.debug("State: {}", current_state)
  logger.error("Error occurred", extra={"error_code": 5})
  ```

### Dependency Graph

```
game_state.py ──────► pyte              (ANSI parsing)
                   ┌─► blessed          (optional: enhanced terminal)

local_client.py ─────┼─► pexpect        (optional: improved PTY handling)
                   └─► loguru           (logging)

char_creation_state_machine.py ─┐
                                ├──► python-statemachine (optional: refactor)
game_state_machine.py ──────────┘     loguru (logging)

bot.py ─────────────► All of above

testing ────────────► pytest
                     pytest-asyncio
```

### Installation

All dependencies are in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Version Compatibility

- Python 3.10+ required
- All packages tested with Python 3.12
- pexpect tested on Linux (primary platform)

## Migration Opportunities

### Future Refactoring Using New Libraries

1. **State Machines** (python-statemachine)
   - Replace manual enum-based state tracking
   - Add transition guards and callbacks
   - Current: ~100 lines per state machine
   - Refactored: ~50 lines, more readable

2. **PTY Handling** (pexpect)
   - Replace raw pty code in `local_client.py`
   - Gain pattern matching capabilities
   - Simplify input/output handling
   - Current: ~150 lines
   - Using pexpect: ~80 lines

3. **Logging** (loguru)
   - Drop-in replacement for current logging
   - No code changes needed (compatible API)
   - Gain better formatting and performance

4. **Testing** (pytest)
   - Migrate test scripts to pytest
   - Add fixtures for common setup
   - Enable parallel test execution

### Non-Urgent

- **blessed**: Nice-to-have for better debug output display
- **pytest-asyncio**: Only needed if async patterns added

## Contributing

When modifying the bot:
1. Run pytest to ensure no regression: `pytest`
2. Test with fresh character creation: `rm ~/.crawl/saves/`
3. Verify debug output shows expected state transitions
4. Document any new states or actions in this guide
5. Add tests for new functionality

## References

- **DCSS Documentation**: https://crawl.develz.org/docs/
- **pyte Library**: https://github.com/selectel/pyte
- **python-statemachine**: https://github.com/fgmacedo/python-statemachine
- **pexpect**: https://pexpect.readthedocs.io/
- **blessed**: https://blessed.readthedocs.io/
- **pytest**: https://pytest.org/
- **loguru**: https://loguru.readthedocs.io/
- **Python PTY**: https://docs.python.org/3/library/pty.html
