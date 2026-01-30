# DCSS Bot: Copilot Instructions

This codebase implements an automated bot for Dungeon Crawl Stone Soup (DCSS) that controls the game through a local PTY (pseudo-terminal) subprocess. This file guides AI agents on the architecture, critical patterns, and workflows.

## Architecture Overview

**Three-Layer Design**: LocalCrawlClient (PTY I/O) → GameStateParser (Screen Analysis) → DCSSBot (Decision Logic)

```
[PTY Process] ←→ [LocalCrawlClient] → [ScreenBuffer + pyte] → [GameStateParser]
                                            ↓
                                  [DCSSBot._decide_action]
                                    (state machines guide decisions)
                                            ↓
                                  [UnifiedBotDisplay] (12-line activity panel)
```

### Key Components

1. **LocalCrawlClient** (`local_client.py`): Manages Crawl subprocess via PTY
   - **Critical**: Uses `cbreak mode` (not raw): `ICANON` disabled, `ECHO` enabled, `ISIG` enabled
   - Why cbreak: Crawl's ncurses needs character-by-character input WITH echo feedback for menu navigation
   - `read_output(timeout=X.X)` reads with select() - must respect full timeout duration (v1.1 bug: line 172 had premature break)
   - Writes single characters via `send_command(char)` for menu navigation and name entry

2. **ScreenBuffer** (bot.py lines 21-55): pyte-based terminal emulation - PRIMARY SOURCE OF GAME STATE
   - **CRITICAL**: The pyte buffer is the authoritative, complete game state
   - Raw PTY output contains only ANSI code DELTAS (incremental changes), not complete screen
   - pyte buffer ACCUMULATES all deltas into a 160x40 character grid, maintaining full reconstructed state
   - `update_from_output()` feeds raw PTY output to pyte Stream for accumulation
   - `get_screen_text()` returns the complete, accurate game state for decision making
   - Used for BOTH game state decisions AND visual screenshots
   - Example: Raw output may have `[1;33H` cursor code, but buffer has complete "J   endoplasm" in monsters section

3. **GameStateParser** (`game_state.py`): Regex-based screen text extraction from pyte buffer
   - Parses TUI display text (from pyte buffer) as source of truth for game state
   - Extracts from TUI: health, mana, dungeon level, experience, visible enemies list
   - Uses regex patterns like `r'Health: (\d+)/(\d+)'` for health extraction
   - Enemy detection: Parses monsters section from TUI line 21 (format: `X   creature_name`)
   - Must handle incomplete data gracefully (some screens lack certain fields)
   - **IMPORTANT**: Always receive text from `screen_buffer.get_screen_text()`, NOT from raw `last_screen`
   - **DEPRECATED**: Message parsing and raw PTY output parsing are no longer used for decisions (messages ephemeral, raw output is delta-only)

4. **DCSSBot** (`bot.py`): Main orchestrator
   - **Critical state variables**:
     - `gameplay_started`: Once True, stays True (no resets mid-game)
     - `last_screen`: Current raw PTY output with ANSI codes
     - `action_reason`: String explaining why last action was chosen (set via `_return_action()`)
   - **Unified display**: Shows Crawl TUI + 12-line activity panel via UnifiedBotDisplay
   - **Screenshot logging**: Auto-saves `logs/screens_TIMESTAMP/` with three formats:
     - `NNNN_raw.txt`: Raw output + ANSI codes
     - `NNNN_clean.txt`: Text only (no codes)
     - `NNNN_visual.txt`: Accumulated buffer state with borders

## Critical Workflows & Patterns

### 1. Main Loop Architecture (bot.py `run()` method, lines 765-880)

```python
while self.move_count < max_steps:
    response = self.ssh_client.read_output(timeout=3.0)      # GET RAW OUTPUT (DELTA)
    if response:
        self.last_screen = response                          # Store raw for logging
        self.screen_buffer.update_from_output(response)      # Accumulate into pyte buffer
        self.parser.parse_output(response)                   # Extract state (parser uses buffer)
    
    # CRITICAL: Use pyte buffer text, not raw output
    screen_text = self.screen_buffer.get_screen_text()       # Get COMPLETE reconstructed state
    action = self._decide_action(screen_text)                # DECIDE ACTION (based on buffer, not delta)
    if action:
        self.ssh_client.send_command(action)                 # SEND ACTION
        self._save_debug_screen(self.last_screen, ...)       # LOG SCREEN
```

**Critical architecture principle** (v1.4+): 
- Raw PTY output (`response`) is only a DELTA - it contains ANSI codes for changed regions, not complete text
- pyte buffer ACCUMULATES all deltas into a complete 160x40 character grid
- **Decision logic MUST use `screen_buffer.get_screen_text()` (complete state), NOT `last_screen` (delta)**
- This is why enemy detection failed before v1.4: it was parsing the delta, not the accumulated buffer
- Logging still uses raw output, but decision-making uses buffer

### 2. State Machine Pattern

**CharacterCreationStateMachine** (`char_creation_state_machine.py`):
- Detects menu type by scanning cleaned text for markers like `"Strength"`, `"choose a job"`
- Returns state names: `'startup'`, `'species'`, `'class_select'`, `'background'`, `'skills'`, `'error'`
- Used during `_local_startup()` to auto-navigate menus
- Screenshots now saved for each menu transition (v1.2 enhancement, lines 1420-1429)

**GameStateMachine** (`game_state_machine.py`):
- High-level states: DISCONNECTED → CONNECTED → GAMEPLAY
- Used by state tracker to validate game progression
- Less critical than CharCreationStateMachine (gameplay logic uses flags more than states)

### 3. Decision Logic Pattern

**`_decide_action()` method** (bot.py, lines 1090-1400):
- Follows priority order: level-up → more prompts → menu → gameplay
- **Gameplay Actions**: All decisions based on TUI display state (not message stream)
  - Enemy detection: Calls `_detect_enemy_in_range()` which parses TUI monsters section
  - Health tracking: Reads from TUI status line (not messages)
  - Threat assessment: Based on what is visible NOW on the TUI display
- **TUI-First Principle** (v1.3+): 
  - TUI display is the complete game state snapshot at any moment
  - Messages are ephemeral and scroll off - should not be used for decisions
  - Example: Enemy detection checks line 21, char 41+ for monster list, not "quivered" message
- **Enemy Detection Example**:
  ```python
  # _detect_enemy_in_range() ONLY looks at TUI monsters section
  # Format: X   creature_name (where X is creature symbol)
  enemy_detected, enemy_name = self._detect_enemy_in_range()
  if enemy_detected:
      return self._return_action('f', f"Flee from {enemy_name}")
  ```
- **Action returns**: Use `_return_action(command, reason)` helper (lines 1050-1054)
  - Sets `self.action_reason` for activity log
  - Example: `return self._return_action('o', "Auto-explore (health: 75%)")`

### 4. Screenshot Capture Pattern

Called from 7 locations in gameplay loop (example line 859):
```python
if self.last_screen:
    self._save_debug_screen(self.last_screen, f"Move {self.move_count}: Sending '{action}'")
```

**Character creation menus** (lines 1420-1429):
- Maps state to screenshot label: `'species'` → `'CHARACTER CREATION: Species Selection'`
- Saved BEFORE making selection (captures menu before user input)
- Includes: initial menu (0001), race (0002), class (0003), background (0004), skills (0005), then gameplay

## Documentation Maintenance

**Critical**: These documentation files are essential for developer understanding. Always update them when making changes:

1. **CHANGELOG.md** - Records all user-facing changes
   - Update with every bug fix, feature, or enhancement
   - Include version number and date
   - Explain what changed and why (not just "fixed bug")
   - Reference related code locations when helpful
   - Example: "Fixed undefined `complete_screen` variable crash in gameplay loop (bot.py lines 793-802)"

2. **README.md** - Project overview and quick facts
   - Keep feature list in sync with actual implementation
   - Update installation instructions if dependencies change
   - Maintain list of working/broken features
   - Should be readable by non-developers (high-level perspective)

3. **ARCHITECTURE.md** - Technical design and data flow
   - Update component descriptions when adding/removing modules
   - Maintain accuracy of data flow diagrams
   - Document architectural decisions and trade-offs
   - Reference specific line numbers for implementation examples
   - Update "Recent Improvements" section with bug fixes and optimizations

4. **DEVELOPER_GUIDE.md** - How to work on the code
   - Update "Recent Updates" section with new fixes and features
   - Add patterns when discovering new conventions
   - Document new testing approaches
   - Update example code snippets to match current implementation

5. **QUICK_START.md** - Getting started guide
   - Keep usage examples current
   - Update with new command-line flags
   - Maintain "What to Expect" section with accurate behavior
   - Document new features (e.g., new screenshot types)

**Why This Matters**: These docs are the primary knowledge transfer mechanism. When an AI agent or developer reads the code, they first read the docs to understand structure. Stale docs cause confusion and incorrect changes.

**Update Rule**: Every non-trivial change should touch at least one documentation file. If you can't explain why a change is needed in the docs, reconsider if it should exist.

## Project-Specific Conventions

### Logging & Activity Panel
- Use `logger.info()`, `logger.debug()`, `logger.warning()`, `logger.error()` (from loguru)
- Activity messages logged via `UnifiedBotDisplay.add_activity(msg, level)`
- Levels: `"success"` (✓), `"info"` (ℹ), `"warning"` (⚠), `"error"` (✗), `"debug"` (⚙)
- Timestamps auto-added in format `[HH:MM:SS]`

### Testing
- Located in `tests/` with conftest.py fixtures
- Run with `bash run_tests.sh` or `pytest tests/`
- All 70 tests must pass (as of v1.3: 59 original + 11 real game screen validation tests)
- Mock fixtures in conftest: `char_creation_state_machine`, `game_state_parser`, `game_state_tracker`
- Real game screen fixtures: `tests/fixtures/game_screens/` - 4 representative game states

### File Organization
- Core bot logic: `bot.py` (1787 lines - large, but organized by method type)
- PTY subprocess: `local_client.py` (291 lines)
- Game state extraction: `game_state.py` (285 lines)
- State machines: `char_creation_state_machine.py`, `game_state_machine.py`
- Display: `bot_unified_display.py` (227 lines)
- Entry point: `main.py` (uses argparse for --steps, --debug, --crawl-cmd)

## Common Pitfalls to Avoid

1. **Using raw output for decision logic**: BUG - Raw PTY output is only ANSI code deltas, not complete text. Must use `screen_buffer.get_screen_text()` for all game state decisions (enemy detection, health tracking, etc). This was the root cause of v1.3 enemy detection failures.

2. **Undefined variables**: Bug v1.2 used `complete_screen` instead of `self.last_screen` (crashed gameplay loop). Always use `self.last_screen`.

3. **Empty string truthiness**: `if response:` is False for `""`. Must check `if response:` before using, not `if response is not None:`.

3. **Contradictory state logic**: Don't nest gameplay checks inside `elif not self.state_tracker.in_gameplay()` (v1.2 issue). Use simple if/elif/else flow once `gameplay_started` is True.

4. **Gameplay state reset**: Once `self.gameplay_started = True`, never set it back to False mid-game. State is one-way transition.

5. **Message dependency**: Messages are ephemeral, scroll off-screen, and are unreliable sources of game state. **NEVER** use messages like "quivered", "comes into view", "no target in view" for decisions. Always use TUI display as primary source:
   - ❌ BAD: `if "quivered" in self.last_screen:  # Enemy detected`
   - ✅ GOOD: `enemy, name = self._detect_enemy_in_range()  # Parses TUI monsters section`
   - This affects: enemy detection, health tracking, game state verification, threat assessment

6. **ANSI code handling**: Raw PTY output includes ANSI codes. Use:
   - `self._clean_ansi(output)` for text parsing/regex
   - `self.last_screen` (raw with codes) for parsing
   - Store raw in `_save_debug_screen()` for debugging

## Development Workflows

### Running the Bot
```bash
python main.py --steps 100 --debug
```
Outputs: Session log to `logs/bot_session_YYYYMMDD_HHMMSS.log`, screenshots to `logs/screens_YYYYMMDD_HHMMSS/`.

### Running Tests
```bash
bash run_tests.sh
```
Or individual test: `pytest tests/test_bot.py::test_character_creation_flow -v`.

### Adding New Game Logic
1. Add action decision in `_decide_action()` using `_return_action(command, reason)`
2. If detects new game state: add extraction logic to `GameStateParser.parse_output()`
3. If adds new menu: update `CharacterCreationStateMachine` with detection pattern
4. Add unit test to verify state detection (use `game_state_parser` fixture)

### Debugging Game Loop Issues
1. Check `logs/bot_session_*.log` for error messages and stack traces
2. Check `logs/screens_*/` for visual history of what the bot saw
3. Add `logger.debug()` calls around suspicious code (enable with `--debug` flag)
4. Review `action_reason` in activity panel to understand decision flow

## Version History & Recent Fixes

- **v1.3** (Jan 30, 2026): TUI-First Architecture - Removed all message stream dependency, enemy detection now solely based on TUI monsters section
- **v1.2** (Jan 29, 2026): Fixed undefined `complete_screen` crash, contradictory gameplay state logic, added per-menu screenshots
- **v1.1** (Jan 28): Fixed PTY timeout bug (v1.0 exit after ~0.5s instead of full timeout)
- **v1.0** (Jan 27): SSH removal, integration of python-statemachine and blessed frameworks

Reference CHANGELOG.md for full history.
