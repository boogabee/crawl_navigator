# Project Structure (v1.8+)

## Overview

The DCSS Bot project has been reorganized into a clean, professional structure with clear separation of concerns. This document describes the directory layout and where to find specific functionality.

## Root Level (Essential Files Only)

```
crawl_navigator/
├── main.py              # CLI entry point with argparse
├── README.md            # Project overview (user-facing)
├── LICENSE              # License file
├── pytest.ini           # Pytest configuration
├── requirements.txt     # Python dependencies
└── .gitignore           # Git ignore rules
```

**Philosophy**: Only the absolute essentials at root. All code is organized into packages.

## Source Code: `src/` Package

Core bot logic organized by functionality and concern:

### `src/bot.py` (2200+ lines)
**Main orchestrator and gameplay loop**
- `DCSSBot` class: Main bot implementation
- `ScreenBuffer` class: Pyte-based terminal emulation (PRIMARY SOURCE OF GAME STATE)
- Game loop: `run()` method coordinates all gameplay
- State tracking: `gameplay_started`, `move_count`, etc.
- Decision logic: `_decide_action()` routes to DecisionEngine
- Helper methods: Enemy detection, health tracking, combat decisions
- Activity logging: Timestamped messages to unified display
- Screenshot capture: Auto-saves game screens to logs/

### `src/local_client.py` (335 lines)
**PTY subprocess management**
- `LocalCrawlClient` class: Subprocess execution and I/O
- PTY setup: Cbreak mode for proper ncurses handling
- Command sending: Character-by-character input with echo
- Output reading: Select-based timeout reading
- Terminal mode: No raw mode (allows signal handling)

### `src/game_state.py` (550 lines)
**Game state parsing and extraction**
- `GameStateParser` class: Screen text extraction via regex
- `GameState` dataclass: Parsed game state snapshot
- `InventoryItem` dataclass: Item representation
- Extraction methods: Health, mana, dungeon level, enemies, inventory
- **CRITICAL**: Uses text from `screen_buffer.get_screen_text()` (complete state), not raw PTY deltas

### `src/decision_engine.py` (372 lines)
**Rule-based decision system (Phase 3)**
- `Priority` enum: CRITICAL→URGENT→HIGH→NORMAL→LOW
- `Rule` dataclass: name, priority, condition, action
- `DecisionContext` dataclass: 25+ game state fields
- `DecisionEngine` class: Rule evaluation engine
- Default rules: 25 rules covering all game situations
- `create_default_engine()`: Factory for default engine

### `src/tui_parser.py`
**TUI layout parsing utilities**
- `DCSSLayoutParser` class: Parses TUI sections
- Extracts: Character panel, message log, monsters section
- Used for structured screen analysis

### `src/state_machines/` Subpackage
State machine implementations for game automation

#### `char_creation_state_machine.py`
- `CharacterCreationStateMachine` class: Automaton for character creation
- States: startup, species, class, background, skills, abilities, difficulty
- Menu detection: Recognizes menu types from screen text
- Transition logic: Determines next action for each state
- Used by: `_local_startup()` to navigate character creation

#### `game_state_machine.py`
- `GameStateMachine` class: High-level game state tracking
- States: DISCONNECTED, CONNECTED, GAMEPLAY, MENU, COMBAT, QUIT, ERROR
- Used for: Overall game flow validation

### `src/display/` Subpackage
Display components for unified UI

#### `bot_unified_display.py` (218 lines)
- `UnifiedBotDisplay` class: Unified game TUI + activity panel
- Activity panel: 12-line scrolling message log
- Color coding: Success (green), info (default), warning (yellow), error (red), debug (cyan)
- Timestamps: Auto-added in HH:MM:SS format
- Used by: Bot main loop for all UI rendering

### `src/utils/` Subpackage
Utility modules

#### `credentials.py`
- `CRAWL_COMMAND`: Crawl executable path (default: `/usr/games/crawl`)
- Separated from main code for easy configuration
- Imported by: `main.py` and test fixtures

## Test Suite: `tests/` Package

Comprehensive test coverage (240 tests, 100% passing)

```
tests/
├── conftest.py                              # Pytest fixtures
├── test_blessed_display.py                  # Display tests
├── test_bot.py                              # Bot integration tests
├── test_combat_decisions.py                 # Combat logic tests
├── test_decision_engine.py                  # Engine unit tests
├── test_decision_engine_integration.py      # Engine integration
├── test_engine_vs_legacy.py                 # Comparison tests (26 new)
├── test_equipment_system.py                 # Equipment tests
├── test_game_state_parser.py                # Parser tests
├── test_inventory_and_potions.py            # Inventory tests
├── test_inventory_detection.py              # Item detection tests
├── test_phase_3b_wrapper.py                 # Engine integration tests
├── test_real_game_screens.py                # Real screen tests
├── test_statemachine.py                     # State machine tests
└── fixtures/                                # Test data
    └── game_screens/                        # Real DCSS screen samples
```

### Fixtures (in `conftest.py`)
- `crawl_command`: Crawl executable path
- `char_creation_state_machine`: Fresh state machine instance
- `game_state_tracker`: Fresh game state machine
- `game_state_parser`: Fresh parser instance
- `game_screens`: Loaded real screen fixtures
- Plus 5 specialized screen fixtures: startup, single_enemy, multiple_enemies, etc.

### Test Organization
- **Unit tests**: Individual function and class tests
- **Integration tests**: Multi-component interaction tests
- **Real game tests**: Tests using real DCSS screen captures
- **Comparison tests**: Engine vs legacy behavior validation

## Documentation: `docs/` Package

Comprehensive documentation (55+ files, 760KB total)

### Core Documentation
- **ARCHITECTURE.md**: Technical design and data flow
- **DEVELOPER_GUIDE.md**: Developer workflows and patterns
- **QUICK_START.md**: Quick start and usage guide
- **CHANGELOG.md**: Version history and changes
- **README.md**: Project overview

### Analysis & Reports
- **CODE_REVIEW_*.md**: Code quality assessments
- **LEGACY_CODE_ANALYSIS.md**: Legacy code audit
- **PERFORMANCE_TEST_*.md**: Performance analysis

### Implementation Guides
- **DECISION_ENGINE_*.md**: DecisionEngine documentation (multiple files)
- **EQUIPMENT_SYSTEM.md**: Equipment system guide
- **INVENTORY_SYSTEM.md**: Inventory management guide

### Phase Documentation
- **PHASE_3_*.md**: Phase 3 refactoring documentation
- **PHASE_3B_*.md**: Phase 3b implementation details

### Other
- Validation reports, testing documentation, setup guides, etc.

## Examples & Debug: `examples/` Package

Example code and debug utilities

```
examples/
├── example_tui_parsing.py           # TUI parsing examples
├── test_health_debug.py             # Health tracking debug tools
├── debug_crawl_startup.py           # Startup sequence debugging
├── bot_display.py                   # Legacy display utilities
└── examples_statemachine_blessed.py # State machine examples
```

These are non-production helper scripts for development and debugging.

## Scripts: `scripts/` Package

Utility scripts for common operations

```
scripts/
├── run_tests.sh                     # Test runner (activates venv)
└── crawl_wrapper.sh                 # Crawl launch wrapper
```

### `run_tests.sh`
- Activates virtual environment
- Checks dependencies
- Compiles all Python files (syntax check)
- Runs full pytest suite

### `crawl_wrapper.sh`
- Wrapper for launching Crawl
- Handles terminal setup
- Sets environment variables as needed

## Logs: `logs/` Directory

Runtime logs and screenshot captures (created during execution)

```
logs/
├── bot_session_YYYYMMDD_HHMMSS.log    # Session log file
└── screens_YYYYMMDD_HHMMSS/           # Screenshot directory
    ├── 0001_raw.txt                   # Raw output with ANSI codes
    ├── 0001_clean.txt                 # Clean text
    ├── 0001_visual.txt                # Visual representation
    ├── ...
    └── index.txt                      # Screenshot index
```

**Auto-created**: New directory for each bot run with timestamp

## Import Patterns

### Standard Imports (with new structure)
```python
# From main.py or tests
from src.bot import DCSSBot
from src.local_client import LocalCrawlClient
from src.game_state import GameStateParser, GameState
from src.decision_engine import DecisionEngine, Priority
from src.state_machines.char_creation_state_machine import CharacterCreationStateMachine
from src.display.bot_unified_display import UnifiedBotDisplay
from src.utils.credentials import CRAWL_COMMAND
```

### Running Tests
```bash
# Full test suite
pytest tests/ -v

# Specific test file
pytest tests/test_bot.py -v

# Specific test function
pytest tests/test_bot.py::TestBotInitialization::test_bot_initializes -v

# With coverage
pytest tests/ --cov=src
```

### Virtual Environment
```bash
# Activate venv
source venv/bin/activate

# Or use full path
/home/skahler/workspace/crawl_navigator/venv/bin/python main.py --steps 100
```

## Design Principles

### Separation of Concerns
- **src/bot.py**: Game loop orchestration
- **src/local_client.py**: I/O and subprocess management
- **src/game_state.py**: State extraction and parsing
- **src/decision_engine.py**: Decision logic
- **src/state_machines/**: Automation for specific game phases
- **src/display/**: UI rendering

### Layered Architecture
1. **Execution Layer** (local_client.py): PTY I/O
2. **Parsing Layer** (game_state.py): Screen text extraction
3. **Decision Layer** (decision_engine.py): Action selection
4. **Orchestration Layer** (bot.py): Game loop coordination
5. **Display Layer** (display/): UI rendering

### Key Principles
- **Screen buffer as authoritative state**: Accumulated pyte buffer is primary source
- **No message dependency**: Decisions based on TUI display, not ephemeral messages
- **Rule-based decisions**: Declarative rules instead of procedural logic
- **Clean imports**: Organized package structure with clear dependencies

## Quick File Lookup

| Task | Location |
|------|----------|
| Change Crawl command | `src/utils/credentials.py` |
| Modify game loop | `src/bot.py` (run method) |
| Add decision rule | `src/decision_engine.py` (create_default_engine) |
| Add game state parsing | `src/game_state.py` (GameStateParser class) |
| Change menu navigation | `src/state_machines/char_creation_state_machine.py` |
| Modify UI display | `src/display/bot_unified_display.py` |
| Add tests | `tests/test_*.py` |
| Update documentation | `docs/*.md` |
| Run tests | `bash scripts/run_tests.sh` |
| Debug output | `logs/screens_TIMESTAMP/` |

## Version History

**v1.8** (Jan 31, 2026): Project reorganization
- Created src/ package structure with subpackages
- Moved documentation to docs/ (55 files)
- Moved examples to examples/
- Moved scripts to scripts/
- Cleaned root directory (50+ → 6 files)
- All 240 tests passing, zero regressions
- Updated all imports and configurations

Previous versions: See CHANGELOG.md
