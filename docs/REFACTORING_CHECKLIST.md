# Refactoring Action Items Checklist

## Quick Reference for Improvements

### IMMEDIATE WINS (Do First)

- [ ] **ANSIHandler** - Single source for ANSI code stripping
  - File: `create parsers/ansi_utils.py`
  - Replace: `game_state.py._clean_ansi()` + `bot.py._clean_ansi()`
  - Effort: 0.5 hours
  - Impact: Removes code duplication

- [ ] **CachedLayoutParser** - Prevent repeated parsing
  - File: `create parsers/cached_layout.py`
  - Issue: Multiple `DCSSLayoutParser()` instances per decision cycle
  - Effort: 0.5 hours
  - Impact: 20% parsing performance improvement

- [ ] **Move hardcoded patterns to PatternLibrary**
  - File: `create parsers/pattern_library.py`
  - Consolidate: Health, mana, dungeon, inventory, enemy patterns
  - Effort: 1.5 hours
  - Impact: Single source of truth for regex

### HIGH VALUE (Do Next)

- [ ] **Extract TextExtractor base class**
  - File: `create parsers/text_extractors.py`
  - Replace: Similar parsing logic in game_state.py + bot.py
  - Affected:
    - `game_state.py` lines 165-180 (health parsing)
    - `game_state.py` lines 300-350 (inventory parsing)
    - `bot.py` lines 2224-2250 (enemy extraction)
  - Effort: 3 hours
  - Impact: ~90 lines saved, consistent parsing

- [ ] **Consolidate screen state detection**
  - File: `create bot/screen_detectors.py`
  - Replace: `_is_in_shop()`, `_is_item_pickup_menu()`, character creation states
  - Effort: 1.5 hours
  - Impact: Centralized state definitions

- [ ] **Unify logging with ActivityLogger**
  - File: `create bot/activity_logger.py`
  - Replace: Scattered `logger.info()`, `_log_activity()`, `_log_event()`
  - Effort: 1 hour
  - Impact: Consistent logging format + semantic methods

### MAJOR REFACTORS (Complex, Big Payoff)

- [ ] **Refactor _decide_action() with DecisionEngine**
  - File: `create bot/decision_engine.py`
  - Current: 1200+ lines of nested if/elif
  - New: 50 lines using rules
  - Affected: `bot.py` lines 1490-2650+
  - Effort: 6 hours
  - Impact: ~1100 lines saved, dramatically improved readability
  - Risk: Medium (core logic)
  - Test coverage required: 100%

- [ ] **Create MessageInterpreter for game events**
  - File: `create parsers/message_interpreter.py`
  - Consolidate: Level-up, items, combat message parsing
  - Effort: 2 hours
  - Impact: ~50 lines saved, new event system foundation

- [ ] **Create InventoryManager abstraction**
  - File: `create systems/inventory_manager.py`
  - Replace: Scattered inventory logic in bot.py + game_state.py
  - Effort: 2 hours
  - Impact: ~60 lines saved, reusable inventory logic

### STRUCTURAL IMPROVEMENTS

- [ ] **Split bot.py into modules**
  - Create `bot/` package:
    - `bot/__init__.py` - Main DCSSBot class
    - `bot/combat.py` - Combat decision logic
    - `bot/exploration.py` - Exploration logic
    - `bot/inventory.py` - Item management
    - `bot/startup.py` - Character creation
  - Effort: 4 hours
  - Impact: Better organization, ~2500 lines in single file → 400-600 each

- [ ] **Organize parsers into package**
  - Create `parsers/` package:
    - `parsers/__init__.py`
    - `parsers/game_state.py` - Existing game_state.py
    - `parsers/tui.py` - TUI layout parsing
    - `parsers/ansi_utils.py` - ANSI handling
    - `parsers/pattern_library.py` - Regex patterns
    - `parsers/text_extractors.py` - Text extraction
    - `parsers/message_interpreter.py` - Message parsing
  - Effort: 2 hours
  - Impact: Better code organization

- [ ] **Create config module for constants**
  - File: `create config/game_constants.py`
  - Move: Health thresholds, AC defaults, item keywords, message patterns
  - Effort: 1 hour
  - Impact: Easier tuning, single source for magic numbers

### TESTING IMPROVEMENTS

- [ ] **Add tests for PatternLibrary**
  - File: `tests/test_pattern_library.py`
  - Coverage: 10 test cases
  - Effort: 1 hour

- [ ] **Add tests for TextExtractor**
  - File: `tests/test_text_extractors.py`
  - Coverage: 15 test cases
  - Effort: 1.5 hours

- [ ] **Add tests for ScreenDetector**
  - File: `tests/test_screen_detectors.py`
  - Coverage: 12 test cases
  - Effort: 1 hour

- [ ] **Add tests for DecisionEngine**
  - File: `tests/test_decision_engine.py`
  - Coverage: 20 test cases (rules + priorities)
  - Effort: 2.5 hours

---

## PRIORITY ROADMAP

### Week 1: Low-Hanging Fruit
- [ ] ANSIHandler (0.5h)
- [ ] CachedLayoutParser (0.5h)
- [ ] PatternLibrary (1.5h)
- [ ] Create parsers package structure (1h)
- **Total: 3.5 hours** → **~40 lines saved**

### Week 2: Consolidation
- [ ] TextExtractor (3h)
- [ ] ScreenDetector (1.5h)
- [ ] ActivityLogger (1h)
- [ ] Add tests for above (2h)
- **Total: 7.5 hours** → **~170 lines saved**

### Week 3: Major Refactor
- [ ] DecisionEngine (6h)
- [ ] Split bot.py structure (4h)
- [ ] Add comprehensive tests (2.5h)
- **Total: 12.5 hours** → **~1100 lines saved**

### Week 4: Polish
- [ ] MessageInterpreter (2h)
- [ ] InventoryManager (2h)
- [ ] Create config module (1h)
- [ ] Documentation + final tests (2h)
- **Total: 7 hours** → **~110 lines saved**

---

## FILE STRUCTURE AFTER REFACTORING

```
crawl_navigator/
├── parsers/                    # NEW: Parsing utilities
│   ├── __init__.py
│   ├── game_state.py          # Existing, moved
│   ├── tui.py                 # Existing, moved
│   ├── ansi_utils.py          # NEW
│   ├── pattern_library.py     # NEW
│   ├── text_extractors.py     # NEW
│   ├── message_interpreter.py # NEW
│   └── cached_layout.py       # NEW
├── bot/                        # REFACTORED: Split from bot.py
│   ├── __init__.py            # Main DCSSBot
│   ├── core.py                # Main game loop
│   ├── combat.py              # Combat logic
│   ├── exploration.py         # Exploration logic
│   ├── inventory.py           # Inventory management
│   ├── startup.py             # Character creation
│   ├── display.py             # Display + logging
│   ├── screen_detectors.py    # NEW
│   ├── decision_engine.py     # NEW
│   └── activity_logger.py     # NEW
├── systems/                    # NEW: Game systems
│   ├── __init__.py
│   └── inventory_manager.py   # NEW
├── config/                     # NEW: Configuration
│   ├── __init__.py
│   └── game_constants.py      # NEW
├── tests/
│   ├── test_pattern_library.py        # NEW
│   ├── test_text_extractors.py        # NEW
│   ├── test_screen_detectors.py       # NEW
│   ├── test_decision_engine.py        # NEW
│   └── ...existing tests...
├── main.py                     # Entry point (no changes)
├── local_client.py            # PTY handling (no changes)
└── ...
```

---

## METRICS TO TRACK

| Metric | Before | Target | Method |
|--------|--------|--------|--------|
| Total Python lines | ~2500 | ~1100 | `wc -l **.py` |
| Cyclomatic complexity | High | Medium | pylint |
| Test coverage | 95% | 98% | pytest --cov |
| Duplicate code (%) | 15% | 5% | radon |
| Avg method size | 30 lines | 15 lines | custom script |

---

## VALIDATION CHECKLIST

After each refactoring:
- [ ] All 146 tests still pass
- [ ] No new Pylint warnings
- [ ] Code coverage maintained ≥95%
- [ ] Manual testing: 50 step game run
- [ ] Performance: No noticeable slowdown
- [ ] Documentation: Update DEVELOPER_GUIDE.md

---

## NOTES

- **Start small**: ANSIHandler and CachedLayoutParser are safe first steps
- **Test incrementally**: Each module should have accompanying tests
- **Document as you go**: Update docstrings and module README
- **One feature at a time**: Don't refactor multiple areas simultaneously
- **Git commits**: One commit per logical unit (not one per file)
