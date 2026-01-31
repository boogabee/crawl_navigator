# Architecture and Design

## Overview

The DCSS Bot is an automated player for Dungeon Crawl Stone Soup that uses a local PTY (pseudo-terminal) interface to interact with the game programmatically.

## Core Components

### LocalCrawlClient (`local_client.py`)
Manages subprocess execution of Crawl via PTY:
- **PTY Setup**: Creates pseudo-terminal with `os.fork()` and `pty.openpty()`
- **Terminal Emulation**: Sets cbreak mode (character-by-character input with echo) for proper ncurses handling
  - **Cbreak Mode Details**: Disables line buffering (`ICANON`), enables echo and signal processing, non-blocking reads
  - **Why Cbreak**: Crawl's ncurses menus require character-by-character input without full line buffering
  - **Echo Benefit**: Provides visual feedback during menu navigation and name entry
- **Process Management**: Handles startup, termination, and I/O buffering
- **Command Sending**: Writes game commands to PTY
- **Output Reading**: Uses `select()` with timeouts to read response data

### GameStateParser (`game_state.py`)
Parses PTY output to extract game state:
- **Primary Source**: Reconstructed screen state from pyte buffer (complete, accumulated game state)
- **Buffer vs Raw**: Processes text from `screen_buffer.get_screen_text()`, not raw PTY deltas
- Health/mana tracking (from TUI status line)
- Character location (dungeon branch, depth level)
- Threat detection via TUI monsters section (line 21, format: `X   creature_name`)
- Item identification
- **Note**: Message parsing is no longer used for decision logic (messages are ephemeral, raw PTY output is delta-only)

### DCSSBot (`bot.py`)
Main bot logic and game loop:
- **Startup Handling**: Navigates menus and character creation via `_local_startup()`
  - Captures screenshot of each menu (species, class, background, skills selections)
  - Descriptive labels for easy identification in logs
- **Screen Buffering**: Uses `pyte.Screen` for accurate ANSI code parsing and display
- **Gameplay Loop**: Executes actions in `run()` method
  - Fixed: Now reliably captures all gameplay screens
  - Fixed: No more contradictory state messages
- **Decision Making**: Evaluates game state and chooses actions
  - Consistent gameplay state tracking (once started, remains started)
- **Unified Display**: Shows game board + 12-line activity panel with bot actions and events
- **Activity Logging**: Logs timestamped messages with color-coded severity levels to the activity panel
  - Action reasons now consistently accurate

### CharacterCreationStateMachine (`char_creation_state_machine.py`)
Automates character creation menu navigation:
- Tracks current menu state (name entry, species selection, job selection, etc.)
- Detects menu types from screen content
- Provides expected choices for each state
- Detects stuck/loop conditions

### UnifiedBotDisplay (`bot_unified_display.py`)
Unified terminal interface combining game output with activity panel:
- **Game Display**: Full Crawl TUI shown at top of terminal
- **Activity Panel**: 12-line panel showing timestamped bot actions and events
- **Color Coding**: Messages color-coded by severity (✓ success, ℹ info, ⚠ warning, ✗ error, ⚙ debug)
- **Message History**: Maintains up to 100 timestamped activity messages
- **Terminal Aware**: Adapts to terminal size and respects ANSI color support

### GameStateTracker (`game_state_machine.py`)
High-level game state tracking:
- Connection status (disconnected, connected, gameplay)
- Major state transitions
- Error detection and recovery

## I/O Architecture

### PTY Communication Flow
```
Bot Process
    ↓ (send_command)
[LocalCrawlClient]
    ↓ (write to PTY FD)
[Crawl Process]
    ↓ (output to PTY)
[PTY Buffer]
    ↓ (read from PTY FD - timeout handled correctly ✅)
[LocalCrawlClient]
    ↓ (return as string)
Bot Process
    ├→ Update last_screen ✅ (FIXED: was undefined)
    ├→ (feed raw deltas to pyte for accumulation)
[ScreenBuffer - pyte]
    ├→ (accumulate all deltas into complete 160x40 character grid)
    ├→ (get_screen_text() returns complete, authoritative state)
    ├→ (extract health/mana/enemies from complete state)
[GameStateParser]
    ├→ Save screenshot ✅ (Gameplay + all character creation menus)
    └→ (log activity + render)
[UnifiedBotDisplay]
    ├→ Render game screen (top)
    ├→ Add status/move info
    ├→ Render activity panel (bottom 12 lines)
    └→ Display to terminal
```

**Recent Improvements**: 
- (v1.4) Screen Logging & Enemy Detection Improvements
  - Screen logging now has comprehensive error handling with file write validation and logging
  - Enemy detection supports lowercase grouped creatures ("gg  2 goblins")
  - Message artifacts filtered out ("Found X item" no longer triggers combat)
  - Invalid symbols rejected from monster entries (Found, You, The, etc.)
  - All 75 tests passing (+4 new validation tests)
- (v1.4) Pyte Buffer as Primary Source - Changed decision logic to use accumulated pyte buffer state instead of raw PTY deltas
  - Raw PTY output is only ANSI code deltas, not complete screen text
  - Pyte buffer accumulates all deltas into a complete 160x40 character grid
  - `_decide_action()` now uses `screen_buffer.get_screen_text()` for complete game state
  - Fixes enemy detection which was failing when raw output didn't contain creature names
  - This is the authoritative game state representation
- (v1.3) TUI-First Architecture - Refactored all decision logic to use TUI display as sole source of truth
  - Removed message-based enemy detection ("quivered", "comes into view", etc.)
  - `_detect_enemy_in_range()` now parses TUI monsters section only
  - More reliable: TUI reflects actual game state, not ephemeral message stream
- (v1.2) Fixed undefined `complete_screen` variable crash in gameplay loop - now reliably captures all screens
- (v1.2) Fixed contradictory gameplay state logic - simplified state checks to prevent "waiting for gameplay" message after gameplay started
- (v1.2) Added screenshot captures for all character creation menus with descriptive labels
- (v1.1) Fixed critical PTY read timeout bug where `else: break` on line 172 was causing premature exit after ~0.5s instead of respecting the full 2.0s timeout

### Terminal Handling
- **Cbreak Mode**: PTY operates in cbreak mode (character-by-character with echo, not raw)
  - Provides proper input handling for Crawl's ncurses interface
  - Enables echo for visual feedback during name entry and menu navigation
  - Allows signal processing (Ctrl+C, etc.)
  - Uses non-blocking reads (`VMIN=0`, `VTIME=0`) for responsive I/O
- **ANSI Parsing**: pyte library handles ANSI escape sequences from PTY output
- **Screen State**: Accumulates complete screen state, not just deltas
- **Screenshot Logging**: Captures all screens with context labels for debugging
- **Buffering**: select() used for reliable async reads with timeout
- **Unified Display**: UnifiedBotDisplay module combines game view with activity panel
- **Activity Logging**: Timestamped messages with color-coded severity for real-time debugging

## Game State Machine States

1. **DISCONNECTED**: Bot not connected to game
2. **CONNECTED**: Connected but not in gameplay (menus)
3. **GAMEPLAY**: In actual game, can send game commands

## Startup Sequence

1. **PTY Setup**: Create and configure pseudo-terminal
2. **Process Fork**: Spawn Crawl subprocess
3. **Menu Navigation**: 
   - Wait for startup menu → logs "Startup menu detected" ✓
   - Send character name → logs "Sending character name: [name]" ℹ
   - Select menu option → logs "Selecting 'Dungeon Crawl' from menu" ℹ
   - Navigate character creation if needed
   - Or load existing character if available
4. **Gameplay Detection**: Verify Time display visible in output → logs "Gameplay started!" ✓
5. **Ready**: Begin gameplay loop with unified display showing game + activity panel

## Action System

The bot selects actions based on parsed game state:

### Safe Actions
- Movement to adjacent empty tiles
- Resting (.) to recover health
- Opening doors (o + direction)

### Threat Response
- Flee from enemies
- Use escape items
- Find safe resting spots

### Item/Exploration
- Pick up items
- Explore new areas
- Navigate dungeon levels

## Threading Model

- **Main Thread**: Game loop with blocking I/O
- **Read Thread** (optional): Async screen capture (not currently used)
- **No Multi-threading**: Single-threaded for simplicity and reliability

## Terminal State Management

- **Screen Buffer**: Maintains 160x40 character grid using pyte
- **Visual Display**: Shows actual dungeon map, stats, messages
- **Debug Logging**: Timestamped in console
- **Screen Capture**: Saves debug screens for troubleshooting

## Error Handling

- **Timeout Detection**: Kills process if no response after timeout
- **State Stuck Detection**: Detects infinite loops in character creation
- **Invalid Output**: Handles malformed ANSI sequences gracefully
- **Process Death**: Detects and reports when Crawl process terminates

## Dependency Architecture

### Library Integration by Layer

```
┌─────────────────────────────────────────────────────────────┐
│                     Testing & Validation                      │
│        pytest  |  pytest-asyncio  |  test utilities          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Execution & Process Layer                  │
│  local_client.py  ←→  pexpect (optional)  ←→  loguru        │
│      (PTY I/O)        (enhanced PTY)      (logging)          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Display & Parsing Layer                    │
│     game_state.py  ←→  pyte (ANSI)  ←→  blessed (display)   │
│    (state extract)   (terminal emu)    (terminal control)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   State Machine Layer                         │
│  char_creation_state_machine.py  ←→  python-statemachine    │
│  game_state_machine.py                (optional refactor)    │
│      (current: manual)                (future: framework)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Application Logic Layer                    │
│                        bot.py                                 │
│                 (orchestration & decisions)                   │
└─────────────────────────────────────────────────────────────┘
```

### Core Dependencies

**`pyte` (ANSI Terminal Emulation)**
- **Location in Stack**: Display & Parsing Layer
- **Integration**: Used in `game_state.py` to parse terminal output
- **Why**: Accurate ANSI escape sequence handling, maintains character grid with attributes
- **Current Use**: Mandatory for screen parsing

**`python-dotenv` (Configuration)**
- **Location in Stack**: Configuration layer (implicit)
- **Integration**: Loads environment variables for credentials
- **Why**: Clean separation of sensitive data from code
- **Current Use**: Optional but recommended

### Enhancing Process Layer

**`pexpect` (PTY Interaction)**
- **Location in Stack**: Execution & Process Layer
- **Current Implementation**: Custom PTY code in `local_client.py`
- **Enhancement Path**: Can replace raw PTY handling with pexpect's built-in features
- **Benefits**:
  - Pattern matching for menu detection (replaces regex in state machines)
  - Better timeout and error handling
  - Simplified async I/O
  - Cross-platform reliability
- **Future Usage Example**:
  ```python
  import pexpect
  child = pexpect.spawn('crawl')
  
  # Pattern-based menu detection
  index = child.expect(['select.*species', 'choose.*class', pexpect.TIMEOUT])
  if index == 0:
      # Detected species selection
      child.sendline('d')
  ```
- **Integration Impact**: Would reduce ~50 lines in `local_client.py` and enable pattern-based state transitions

### Enhancing Display Layer

**`blessed` (Advanced Terminal Control)**
- **Location in Stack**: Display & Parsing Layer
- **Current Implementation**: Basic terminal output via pyte
- **Enhancement Path**: Complementary to pyte for enhanced display
- **Benefits**:
  - Colored output for bot state display
  - Cursor positioning for debugging
  - Terminal capability detection
  - Better user experience
- **Potential Integration**:
  ```python
  from blessed import Terminal
  term = Terminal()
  
  # Display bot state in colors
  print(term.bold_red('Game State: ') + term.green(current_state))
  print(term.move(0, 0) + term.cyan(board_display))
  ```
- **Integration Impact**: Enhances debugging and bot monitoring without changing core logic

### Enhancing State Machine Layer

**`python-statemachine` (State Machine Framework)**
- **Location in Stack**: State Machine Layer
- **Current Implementation**: Manual enum-based state machines in both state machine files
- **Enhancement Path**: Framework-based state definitions
- **Benefits**:
  - Cleaner, more maintainable state definitions
  - Built-in transition guards and callbacks
  - Automatic transition validation
  - Better for complex state flows
- **Refactoring Opportunity**:
  ```python
  from statemachine import StateMachine, State
  
  class CharCreationStateMachine(StateMachine):
      start = State('Start', initial=True)
      race_selection = State('Species Selection')
      class_selection = State('Class Selection')
      gameplay = State('Gameplay')
      
      select_species = start.to(race_selection)
      select_class = race_selection.to(class_selection)
      enter_game = class_selection.to(gameplay)
  ```
- **Integration Impact**: ~40-50% reduction in state machine code with better readability

### Logging & Debugging

**`loguru` (Enhanced Logging)**
- **Location in Stack**: Cross-cutting concern (all layers)
- **Current Implementation**: Python stdlib `logging` in `local_client.py`
- **Enhancement Path**: Drop-in replacement with better output
- **Benefits**:
  - Cleaner API than stdlib logging
  - Automatic exception logging with context
  - Built-in file rotation and formatting
  - Colored console output
  - Better performance
- **Migration**:
  ```python
  # Current
  logger.info("Current state: %s", current_state)
  
  # With loguru (same or simpler)
  logger = loguru.logger
  logger.info("Current state: {}", current_state)
  logger.debug("Details: {}", {"health": hp, "mana": mana})
  ```
- **Integration Impact**: No breaking changes, gradual migration possible

### Testing & Validation

**`pytest` (Test Framework)**
- **Location in Stack**: Testing & Validation Layer (above all others)
- **Current Implementation**: Manual test scripts (`test_*.py`)
- **Enhancement Path**: Professional pytest-based test suite
- **Benefits**:
  - Automated test discovery and execution
  - Better assertion introspection
  - Fixtures for common setup
  - Parallel test execution
  - CI/CD integration ready
- **Integration Example**:
  ```python
  import pytest
  from char_creation_state_machine import CharacterCreationStateMachine
  
  @pytest.fixture
  def state_machine():
      return CharacterCreationStateMachine()
  
  def test_race_detection(state_machine):
      output = "select your species: [a] human [b] dwarf"
      state_machine.update(output)
      assert state_machine.is_in_race_selection
  ```
- **Integration Impact**: Better code quality through automated testing

**`pytest-asyncio` (Async Testing)**
- **Location in Stack**: Testing & Validation Layer
- **Current Use**: Not needed (no async code currently)
- **Future Use**: If async I/O added to `local_client.py` or bot loop
- **Benefit**: Seamless async test execution with pytest

## Dependency Resolution Order

When the bot starts:

```
1. python-dotenv loads .env (configuration)
2. loguru initializes logging
3. bot.py imports all components:
   - LocalCrawlClient (uses pexpect if enabled)
   - GameStateParser (uses pyte)
   - CharacterCreationStateMachine (uses python-statemachine if refactored)
   - GameStateTracker
4. Crawl process spawned via pexpect/pty
5. Screen updates parsed by pyte → blessed display (optional)
6. State machines track progression
7. Actions executed via pexpect/pty
```

## Migration Strategy for New Libraries

### Phase 1 (Current): Baseline
- Core functionality: pyte, python-dotenv
- Manual state machines working

### Phase 2 (Recommended): Enhanced Logging
- Add loguru for better debugging output
- No code logic changes needed (drop-in replacement)
- Enables better monitoring during development

### Phase 3 (Optional): Process Enhancement
- Migrate PTY handling to pexpect
- Gain pattern matching for state detection
- Simplifies `local_client.py` implementation

### Phase 4 (Refactoring): State Machine Modernization
- Refactor state machines to use python-statemachine
- More maintainable and scalable
- Better for complex state flows

### Phase 5 (Polish): Display Enhancement
- Integrate blessed for colored output
- Improve debugging visualization
- Better user experience

## Performance Implications

| Library | CPU Impact | Memory Impact | I/O Impact | Notes |
|---------|-----------|---------------|-----------|-------|
| pyte | Medium (ANSI parsing) | Medium (screen buffer) | None | Already using |
| python-dotenv | Negligible (init only) | Negligible | None | Already using |
| pexpect | Low | Low | Improves (better buffering) | Optional enhancement |
| blessed | Low | Low | None | Cosmetic only |
| python-statemachine | Negligible | Negligible | None | Code clarity only |
| loguru | Low | Low | Depends on output | Better than stdlib |
| pytest | N/A (testing only) | N/A | N/A | Development only |
| pytest-asyncio | N/A (testing only) | N/A | N/A | Development only |

Overall: Adding these libraries has minimal performance impact, mostly benefits without drawbacks.

## Key Design Decisions

1. **PTY vs Pipes**: PTY chosen for proper terminal emulation and escape sequence handling
2. **pyte Library**: Used for accurate screen buffer instead of regex parsing
3. **Subprocess Forking**: Direct fork/exec for better PTY control than subprocess module
4. **Raw Mode**: Necessary for character-by-character control
5. **Synchronous I/O**: Simpler than async; timeouts prevent blocking
6. **Layered Dependencies**: Each library serves a specific architectural layer
7. **Optional Enhancements**: Most new libraries are optional improvements, not requirements

## Limitations and Challenges

- **Alternate Buffer Mode**: Crawl uses ncurses alternate screen which can cause buffering issues
- **Menu Navigation**: Finding text-based menu patterns requires robust parsing
- **Character Creation**: Multiple choice menus require state machine accuracy
- **Real-Time Display**: Balancing responsiveness with reliability

## Performance Characteristics

- **Startup**: ~5-10 seconds to reach gameplay
- **Action Cycle**: ~2-3 seconds per move (including I/O and display)
- **Memory**: ~50-100MB for main process + screen buffer
- **CPU**: Idle when waiting for input, peaks during ANSI parsing
