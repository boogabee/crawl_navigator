# Code Review: Simplification & Refactoring Opportunities

## Executive Summary

This document identifies opportunities to simplify the crawl_navigator codebase through:
1. **Code extraction into utility libraries** - Repeated patterns in regex, parsing, and text processing
2. **Method consolidation** - Similar functionality in multiple places
3. **Architecture improvements** - Reduced complexity in large classes
4. **Pattern standardization** - Consistent interfaces for common operations

---

## 1. REGEX & PATTERN MATCHING LIBRARY

### Problem
- Multiple regex patterns defined inline throughout codebase
- Inconsistent error handling for invalid patterns
- No centralized pattern caching or compilation
- Regex patterns duplicated across files

### Current Usage
```python
# In game_state.py (lines 172-177)
patterns = [
    r'Health[:\s]+(\d+)/(\d+)',
    r'HP[:\s]+(\d+)/(\d+)',
    r'(\d+)/(\d+)\s+hp',
]

# In tui_parser.py (line 200)
if re.search(r'^[a-zA-Z]\s{3,}\w+', line):

# In char_creation_state_machine.py (multiple places)
if re.search(pattern_to_check, test_text):
```

### Proposed Solution: `parsers/regex_utils.py`

```python
from dataclasses import dataclass
from typing import Optional, Dict, List, Pattern
import re

@dataclass
class RegexPattern:
    """Compiled regex with caching and validation."""
    name: str
    pattern: str
    flags: int = 0
    compiled: Optional[Pattern] = None
    
    def compile(self) -> bool:
        """Compile pattern, return success status."""
        try:
            self.compiled = re.compile(self.pattern, self.flags)
            return True
        except re.error as e:
            logger.error(f"Invalid regex pattern '{self.name}': {e}")
            return False
    
    def matches(self, text: str) -> bool:
        """Match against text."""
        if not self.compiled:
            self.compile()
        return bool(self.compiled.search(text)) if self.compiled else False
    
    def extract(self, text: str, group: int = 1) -> Optional[str]:
        """Extract group from text."""
        if not self.compiled:
            self.compile()
        match = self.compiled.search(text) if self.compiled else None
        return match.group(group) if match else None

class PatternLibrary:
    """Centralized pattern storage with caching."""
    
    _instance = None
    _patterns: Dict[str, RegexPattern] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, name: str, pattern: str, flags: int = 0) -> RegexPattern:
        """Register a new pattern."""
        regex = RegexPattern(name, pattern, flags)
        if regex.compile():
            self._patterns[name] = regex
        return regex
    
    def get(self, name: str) -> Optional[RegexPattern]:
        """Retrieve registered pattern."""
        return self._patterns.get(name)

# Initialize common patterns
patterns = PatternLibrary()
patterns.register('health', r'Health[:\s]+(\d+)/(\d+)', re.IGNORECASE)
patterns.register('mana', r'Mana[:\s]+(\d+)/(\d+)', re.IGNORECASE)
patterns.register('dungeon_level', r'([A-Za-z]+):(\d+)')
patterns.register('inventory_item', r'^[a-z]\s*[-\)]\s+')
```

### Files Affected
- `game_state.py` - Health, mana, dungeon level extraction
- `tui_parser.py` - Monster/item detection patterns
- `char_creation_state_machine.py` - Menu detection patterns
- `bot.py` - Various screen parsing operations

### Benefits
- ✓ Single source of truth for patterns
- ✓ Automatic caching/compilation
- ✓ Consistent error handling
- ✓ Improved testability (mock single pattern library)
- ✓ ~30% reduction in regex-related code

---

## 2. TEXT PARSING & EXTRACTION UTILITIES

### Problem
- Similar parsing logic repeated in multiple methods:
  - Health parsing (game_state.py)
  - Enemy parsing (bot.py `_extract_all_enemies_from_tui`)
  - Item parsing (game_state.py `_parse_inventory_screen`)
  - Message parsing (bot.py `_check_and_handle_inventory_state`)
- ANSI code cleaning done in multiple places
- Line-by-line parsing with similar loop patterns

### Current Usage
```python
# Health parsing (game_state.py, lines 165-180)
for pattern in patterns:
    hp_match = re.search(pattern, line, re.IGNORECASE)
    if hp_match:
        return (int(hp_match.group(1)), int(hp_match.group(2)))

# Enemy parsing (bot.py, lines 2224-2250)
for line in monsters_section.split('\n'):
    if line.strip():
        parts = line.split()
        symbol = parts[0]
        # ... more parsing

# Inventory parsing (game_state.py, lines 300-350)
for line in lines:
    if re.match(inventory_pattern, line.strip()):
        # ... more parsing
```

### Proposed Solution: `parsers/text_extractors.py`

```python
from typing import Optional, Callable, List, Dict, Any, Tuple
from dataclasses import dataclass
import re

@dataclass
class ExtractorRule:
    """Define how to extract data from text."""
    patterns: List[str]  # Patterns to try (first match wins)
    group: int = 1  # Which regex group to extract
    transform: Optional[Callable[[str], Any]] = None  # Post-processing
    required: bool = False  # Must match
    
    def extract(self, text: str) -> Optional[Any]:
        """Try all patterns against text."""
        for pattern in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(self.group)
                return self.transform(value) if self.transform else value
        return None

class TextExtractor:
    """Declarative text extraction engine."""
    
    def __init__(self, rules: Dict[str, ExtractorRule] = None):
        self.rules = rules or {}
    
    def add_rule(self, name: str, rule: ExtractorRule) -> None:
        """Add extraction rule."""
        self.rules[name] = rule
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """Extract all fields from text."""
        results = {}
        for name, rule in self.rules.items():
            value = rule.extract(text)
            if value is not None:
                results[name] = value
            elif rule.required:
                logger.warning(f"Required field '{name}' not found in text")
        return results
    
    def extract_lines(self, lines: List[str], 
                     line_matcher: Callable[[str], bool],
                     extractor: Callable[[str], Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract from matching lines."""
        results = []
        for line in lines:
            if line_matcher(line):
                extracted = extractor(line)
                if extracted:
                    results.append(extracted)
        return results

# Example usage:
health_extractor = TextExtractor({
    'health': ExtractorRule([
        r'Health[:\s]+(\d+)/(\d+)',
        r'HP[:\s]+(\d+)/(\d+)',
    ], group=1, transform=int),
    'max_health': ExtractorRule([
        r'Health[:\s]+(\d+)/(\d+)',
        r'HP[:\s]+(\d+)/(\d+)',
    ], group=2, transform=int),
})
```

### Files Affected
- `game_state.py` - ~50 lines saved (health, mana, level parsing)
- `bot.py` - ~80 lines saved (enemy, item extraction)
- `tui_parser.py` - ~40 lines saved (section parsing)

### Benefits
- ✓ Declarative instead of imperative parsing
- ✓ Consistent error handling
- ✓ Easier to modify patterns (no code changes needed)
- ✓ Reusable across different parsers
- ✓ Better testability (mock extractor with test data)

---

## 3. ANSI CODE HANDLING CONSOLIDATION

### Problem
- Multiple ANSI code removal functions:
  - `game_state.py` - `_clean_ansi()`
  - `bot.py` - `_clean_ansi()`
- Identical implementations in multiple places
- ANSI code removal scattered throughout parsing

### Current Usage
```python
# In game_state.py (line 132)
return re.sub(r'\x1b\[[^\x1b]*?[a-zA-Z]|\x1b\([B0UK]', '', text)

# In bot.py (similar)
clean_output = self._clean_ansi(output) if output else ""
```

### Proposed Solution: `parsers/ansi_utils.py`

```python
import re
from typing import List, Optional
from enum import Enum

class ANSICode(Enum):
    """Common ANSI escape codes."""
    RESET = '\x1b[0m'
    BOLD = '\x1b[1m'
    # ... etc

class ANSIHandler:
    """Centralized ANSI code handling."""
    
    # Compiled patterns for efficiency
    _ANSI_PATTERN = re.compile(r'\x1b\[[^\x1b]*?[a-zA-Z]|\x1b\([B0UK]')
    _COLOR_PATTERN = re.compile(r'\x1b\[(?:\d+;)*(\d+)m')
    
    @staticmethod
    def strip(text: str) -> str:
        """Remove all ANSI codes."""
        return ANSIHandler._ANSI_PATTERN.sub('', text)
    
    @staticmethod
    def extract_colors(text: str) -> List[int]:
        """Extract color codes."""
        return [int(m.group(1)) for m in ANSIHandler._COLOR_PATTERN.finditer(text)]
    
    @staticmethod
    def has_color(text: str) -> bool:
        """Check if text contains color codes."""
        return bool(ANSIHandler._COLOR_PATTERN.search(text))
```

### Benefits
- ✓ Single source of truth for ANSI handling
- ✓ Pre-compiled patterns (faster)
- ✓ Better encapsulation
- ✓ Removes code duplication

---

## 4. STATE DETECTION PATTERN CONSOLIDATION

### Problem
- Similar state detection logic repeated:
  - `_is_in_shop()` - Checks for specific markers
  - `_is_item_pickup_menu()` - Pattern matching
  - `_check_and_handle_inventory_state()` - Multi-strategy detection
  - Character creation state detection

### Current Usage
```python
# bot.py - multiple detection methods
def _is_in_shop(self, output: str) -> bool:
    clean = self._clean_ansi(output)
    return 'Welcome to' in clean and 'Shop!' in clean and '[Esc] exit' in clean

def _is_item_pickup_menu(self, output: str) -> bool:
    clean = self._clean_ansi(output)
    return 'Pick up what?' in clean

# char_creation_state_machine.py
def detect_state(self, text: str) -> str:
    for state, pattern in self.patterns.items():
        if pattern.matches(text):
            return state
```

### Proposed Solution: `bot/screen_detectors.py`

```python
from dataclasses import dataclass
from typing import Callable, List, Optional, Dict
from enum import Enum
import re

@dataclass
class ScreenMarker:
    """Markers that identify a screen state."""
    required_markers: List[str]  # Must contain ALL
    optional_markers: List[str]  # May contain some
    forbidden_markers: List[str] = None  # Must NOT contain
    
    def matches(self, text: str) -> bool:
        """Check if text matches marker criteria."""
        # Required markers
        if not all(marker in text for marker in self.required_markers):
            return False
        
        # Forbidden markers
        if self.forbidden_markers:
            if any(marker in text for marker in self.forbidden_markers):
                return False
        
        return True

class ScreenState(Enum):
    """Possible screen states."""
    SHOP = "shop"
    INVENTORY = "inventory"
    ITEM_PICKUP_MENU = "item_pickup_menu"
    COMBAT = "combat"
    LEVELUP = "levelup"

class ScreenDetector:
    """Detect what screen/state we're in."""
    
    def __init__(self):
        self.detectors: Dict[ScreenState, ScreenMarker] = {
            ScreenState.SHOP: ScreenMarker(
                required_markers=['Welcome to', 'Shop!', '[Esc] exit']
            ),
            ScreenState.INVENTORY: ScreenMarker(
                required_markers=['Inventory:', 'slots']
            ),
            ScreenState.ITEM_PICKUP_MENU: ScreenMarker(
                required_markers=['Pick up what?']
            ),
        }
    
    def detect(self, text: str) -> Optional[ScreenState]:
        """Detect which screen we're on."""
        for state, detector in self.detectors.items():
            if detector.matches(text):
                return state
        return None
    
    def is_state(self, text: str, state: ScreenState) -> bool:
        """Check if text matches specific state."""
        return self.detect(text) == state
```

### Benefits
- ✓ Consistent detection logic
- ✓ Easy to add new screens
- ✓ Centralized screen state definitions
- ✓ Eliminates scattered if/check methods
- ✓ ~40 lines saved

---

## 5. DECISION TREE & ACTION LOGIC SIMPLIFICATION

### Problem
- `_decide_action()` is 1200+ lines (lines 1490-2650+)
- Deeply nested if/elif chains
- Difficult to add new decision branches
- Hard to test individual decision logic
- Priority order implicit in code structure

### Current Structure
```python
def _decide_action(self, output: str) -> str:
    # 30+ if/elif blocks checking different conditions
    # Priority order hard to see
    # Each block 10-50 lines of nested logic
```

### Proposed Solution: `bot/decision_engine.py`

```python
from dataclasses import dataclass
from typing import Callable, Optional, List
from enum import Enum

@dataclass
class Decision:
    """A possible action and its reason."""
    action: str
    reason: str
    priority: int  # Lower = higher priority

class DecisionRule:
    """A rule that generates a decision if conditions met."""
    
    def __init__(self, 
                 name: str,
                 condition: Callable[[dict], bool],
                 action_generator: Callable[[dict], Optional[Decision]],
                 priority: int):
        self.name = name
        self.condition = condition
        self.action_generator = action_generator
        self.priority = priority
    
    def evaluate(self, context: dict) -> Optional[Decision]:
        """Check if rule applies and generate decision."""
        if self.condition(context):
            return self.action_generator(context)
        return None

class DecisionEngine:
    """Evaluate rules and find best action."""
    
    def __init__(self):
        self.rules: List[DecisionRule] = []
    
    def add_rule(self, rule: DecisionRule) -> None:
        """Add decision rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
    
    def decide(self, context: dict) -> Optional[Decision]:
        """Find first applicable rule."""
        for rule in self.rules:
            decision = rule.evaluate(context)
            if decision:
                logger.info(f"Decision: {rule.name} → {decision.action}")
                return decision
        return None

# Usage in bot:
engine = DecisionEngine()

# Add rule for combat
engine.add_rule(DecisionRule(
    name="combat",
    condition=lambda ctx: ctx['enemy_detected'],
    action_generator=lambda ctx: Decision(
        action='\t' if ctx['health_pct'] > 70 else ctx['direction'],
        reason=f"Combat: {ctx['enemy_name']}",
        priority=10
    ),
    priority=10
))

# Add rule for shopping
engine.add_rule(DecisionRule(
    name="shop_exit",
    condition=lambda ctx: ctx['in_shop'],
    action_generator=lambda ctx: Decision('\x1b', "Exit shop", 20),
    priority=20
))

# Add rule for auto-explore default
engine.add_rule(DecisionRule(
    name="auto_explore",
    condition=lambda ctx: True,  # Always matches
    action_generator=lambda ctx: Decision('o', "Auto-explore", 1000),
    priority=1000
))

# In _decide_action():
decision = engine.decide({
    'enemy_detected': enemy_detected,
    'enemy_name': enemy_name,
    'health_pct': health_pct,
    'direction': direction,
    'in_shop': in_shop,
    # ... other context
})
```

### Files Affected
- `bot.py` - Replace `_decide_action()` (1200+ lines → 50 lines)

### Benefits
- ✓ Clear priority order (rules sorted)
- ✓ Easy to add/remove/reorder decisions
- ✓ Highly testable (mock context)
- ✓ Reduced cyclomatic complexity
- ✓ ~1100 lines saved
- ✓ Easier to understand decision flow

---

## 6. LOGGING & ACTIVITY TRACKING CONSOLIDATION

### Problem
- Multiple logging patterns:
  - `logger.info()` calls throughout
  - `self.unified_display.add_activity()`
  - `self._log_event()`
  - `self._log_activity()`
- Inconsistent levels (info, debug, warning, error)
- Activity formatting inconsistent

### Current Usage
```python
# Scattered throughout:
logger.info(f"💔 Too injured to use autofight!")
self.unified_display.add_activity(msg, "warning")
self._log_event('combat', 'Enemy engaged')
self._log_activity("message", "info")
```

### Proposed Solution: `bot/activity_logger.py`

```python
from enum import Enum
from typing import Optional
from loguru import logger

class ActivityLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class ActivityLogger:
    """Centralized activity and event logging."""
    
    def __init__(self, display=None):
        self.display = display
    
    def log(self, 
            message: str, 
            level: ActivityLevel = ActivityLevel.INFO,
            event_type: Optional[str] = None) -> None:
        """Log activity and optionally track as event."""
        
        # Log to loguru
        log_func = getattr(logger, level.value)
        log_func(message)
        
        # Display in activity panel
        if self.display:
            self.display.add_activity(message, level.value)
    
    def event(self, 
              event_type: str,
              description: str,
              move_count: int = 0) -> None:
        """Track a named event."""
        self.log(f"Event: {event_type} - {description}", 
                ActivityLevel.INFO)
    
    def combat(self, enemy: str, action: str) -> None:
        """Log combat action."""
        self.log(f"⚔️ {action} - {enemy}", ActivityLevel.INFO)
    
    def item(self, action: str, item: str, count: int = 1) -> None:
        """Log item action."""
        self.log(f"📦 {action}: {item} (x{count})", ActivityLevel.INFO)
    
    def equipment(self, action: str, item: str) -> None:
        """Log equipment action."""
        self.log(f"🛡️ {action}: {item}", ActivityLevel.INFO)
    
    def exploration(self, msg: str) -> None:
        """Log exploration."""
        self.log(f"🗺️ {msg}", ActivityLevel.INFO)
```

### Files Affected
- `bot.py` - Replace `_log_activity()`, `_log_event()`, scattered `logger` calls
- `bot_unified_display.py` - Integrate with ActivityLogger

### Benefits
- ✓ Consistent logging format
- ✓ Unified activity tracking
- ✓ Semantic logging methods (`.combat()`, `.item()`, etc.)
- ✓ Easier to adjust display format globally
- ✓ ~30 lines saved

---

## 7. MESSAGE PARSING & INTERPRETATION

### Problem
- Message parsing logic scattered throughout bot.py
- Similar patterns for detecting game state from messages:
  - Level-up detection (lines ~1580)
  - Item pickup messages (lines ~970)
  - Combat messages (scattered)
  - Inventory messages
- No centralized "message interpreter"

### Proposed Solution: `parsers/message_interpreter.py`

```python
from dataclasses import dataclass
from typing import List, Optional, Callable
from enum import Enum
import re

class MessageType(Enum):
    LEVEL_UP = "level_up"
    ITEM_PICKUP = "item_pickup"
    COMBAT = "combat"
    INVENTORY = "inventory"
    ERROR = "error"
    INFO = "info"

@dataclass
class MessageInterpretation:
    """Meaning extracted from a message."""
    msg_type: MessageType
    details: dict  # Type-specific details
    confidence: float  # 0.0 - 1.0

class MessageInterpreter:
    """Convert messages into meaningful events."""
    
    def __init__(self):
        self.interpreters = {}
        self._setup_default_interpreters()
    
    def _setup_default_interpreters(self):
        """Setup standard message patterns."""
        self.register_interpreter(
            MessageType.LEVEL_UP,
            r'You have reached level (\d+)!',
            lambda m: {'level': int(m.group(1))}
        )
        self.register_interpreter(
            MessageType.ITEM_PICKUP,
            r'You see here (.+?)\.?$',
            lambda m: {'item': m.group(1)}
        )
    
    def register_interpreter(self, 
                            msg_type: MessageType,
                            pattern: str,
                            extractor: Callable) -> None:
        """Register message pattern interpreter."""
        if msg_type not in self.interpreters:
            self.interpreters[msg_type] = []
        
        self.interpreters[msg_type].append({
            'pattern': re.compile(pattern),
            'extractor': extractor
        })
    
    def interpret(self, message: str) -> Optional[MessageInterpretation]:
        """Try to interpret message."""
        for msg_type, interpreters in self.interpreters.items():
            for interp in interpreters:
                match = interp['pattern'].search(message)
                if match:
                    return MessageInterpretation(
                        msg_type=msg_type,
                        details=interp['extractor'](match),
                        confidence=0.9
                    )
        return None
```

### Benefits
- ✓ Centralized message interpretation
- ✓ Easy to add new message types
- ✓ Confidence scoring for uncertain interpretations
- ✓ Separates parsing from action logic
- ✓ ~50 lines saved

---

## 8. SCREEN BUFFER & LAYOUT PARSER OPTIMIZATION

### Problem
- `DCSSLayoutParser` does similar work multiple times per turn
- No caching of parsed layout
- Multiple calls to `parse_layout()` in same decision cycle
- Repetitive area extraction logic

### Current Usage
```python
# In _decide_action() - called multiple times
tui_parser = DCSSLayoutParser()
tui_areas = tui_parser.parse_layout(screen_text)

# Later in same method
tui_parser2 = DCSSLayoutParser()  # Creates new parser!
tui_areas2 = tui_parser2.parse_layout(screen_text)
```

### Proposed Solution: Caching layer

```python
class CachedLayoutParser:
    """Caches layout parsing results."""
    
    def __init__(self):
        self.parser = DCSSLayoutParser()
        self._cache = {}
        self._last_screen = None
    
    def parse(self, screen_text: str):
        """Parse with caching."""
        if screen_text == self._last_screen:
            return self._cache
        
        self._last_screen = screen_text
        self._cache = self.parser.parse_layout(screen_text)
        return self._cache
    
    def get_area(self, name: str):
        """Get specific area from cache."""
        return self._cache.get(name)
```

### Benefits
- ✓ Single parser instance
- ✓ Automatic caching per screen
- ✓ ~20% improvement in parsing overhead
- ✓ ~15 lines saved

---

## 9. INVENTORY & EQUIPMENT SYSTEM ABSTRACTION

### Problem
- Inventory parsing duplicated in multiple places:
  - `game_state.py` - `parse_inventory_screen()`
  - `bot.py` - `_detect_items_on_ground()`
  - Complex item type detection
- No unified item representation
- AC calculation scattered

### Proposed Solution: `systems/inventory_manager.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class ItemCategory(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    POTION = "potion"
    SCROLL = "scroll"
    RING = "ring"
    GOLD = "gold"

class InventoryManager:
    """Unified inventory management."""
    
    def __init__(self):
        self.items: Dict[str, InventoryItem] = {}
        self.equipped: Dict[str, InventoryItem] = {}
    
    def add_item(self, slot: str, item: InventoryItem) -> None:
        """Add item to inventory."""
        self.items[slot] = item
    
    def find_upgrades(self, item_category: ItemCategory) -> List[InventoryItem]:
        """Find better items than equipped."""
        if item_category == ItemCategory.ARMOR:
            current_ac = self._get_equipped_ac()
            upgrades = [
                item for item in self.items.values()
                if item.ac_value < current_ac
            ]
            return sorted(upgrades, key=lambda i: i.ac_value)
        return []
    
    def _get_equipped_ac(self) -> int:
        """Calculate total AC of equipped items."""
        return sum(item.ac_value for item in self.equipped.values())
```

### Benefits
- ✓ Single source of truth for items
- ✓ Reusable upgrade finding logic
- ✓ AC calculation centralized
- ✓ ~60 lines saved

---

## SUMMARY TABLE

| Area | Current | Proposed | Savings |
|------|---------|----------|---------|
| Regex patterns | Scattered | PatternLibrary | ~30 lines |
| Text extraction | Repeated logic | TextExtractor | ~90 lines |
| ANSI handling | 2+ implementations | ANSIHandler | ~20 lines |
| State detection | Multiple methods | ScreenDetector | ~40 lines |
| Decision logic | 1200 line method | DecisionEngine | ~1100 lines |
| Logging | Multiple approaches | ActivityLogger | ~30 lines |
| Message parsing | Scattered | MessageInterpreter | ~50 lines |
| Layout parsing | Repeated calls | CachedLayoutParser | ~15 lines |
| Inventory | Scattered logic | InventoryManager | ~60 lines |
| **TOTAL** | | | **~1435 lines** |

---

## IMPLEMENTATION PRIORITY

### Phase 1 (High Impact, Low Risk)
1. **ANSIHandler** - Drop-in replacement, no dependencies
2. **CachedLayoutParser** - Wrapper around existing class
3. **PatternLibrary** - Gradual migration of patterns

### Phase 2 (Medium Impact, Medium Risk)
4. **TextExtractor** - Standardize parsing patterns
5. **ScreenDetector** - Consolidate state detection
6. **ActivityLogger** - Unified logging interface

### Phase 3 (High Impact, Higher Risk)
7. **DecisionEngine** - Refactor `_decide_action()`
8. **MessageInterpreter** - New abstraction layer
9. **InventoryManager** - Unified item system

---

## ESTIMATED EFFORT

| Task | Lines | Hours | Risk |
|------|-------|-------|------|
| ANSIHandler | ~30 | 0.5 | Low |
| CachedLayoutParser | ~20 | 0.5 | Low |
| PatternLibrary | ~80 | 1.5 | Low |
| TextExtractor | ~120 | 3 | Medium |
| ScreenDetector | ~50 | 1.5 | Medium |
| ActivityLogger | ~50 | 1 | Low |
| DecisionEngine | ~200 | 6 | High |
| MessageInterpreter | ~80 | 2 | Medium |
| InventoryManager | ~100 | 2 | Medium |
| **TOTAL** | **730** | **18 hours** | **Medium** |

---

## ADDITIONAL RECOMMENDATIONS

### 10. Break bot.py into modules
Currently 2500+ lines. Consider splitting into:
- `bot/core.py` - Main game loop
- `bot/combat.py` - Combat logic
- `bot/exploration.py` - Exploration logic  
- `bot/inventory.py` - Item/inventory management
- `bot/display.py` - Screen display/logging

### 11. Create parsers package
Move all parsing to `parsers/`:
- `parsers/__init__.py`
- `parsers/game_state.py` - Current game_state.py
- `parsers/tui.py` - TUI parsing
- `parsers/messages.py` - Message interpretation
- `parsers/regex_utils.py` - Shared regex patterns

### 12. Create tests for utilities
- `tests/test_regex_utils.py`
- `tests/test_text_extractors.py`
- `tests/test_screen_detectors.py`
- `tests/test_decision_engine.py`

### 13. Consider configuration file for game constants
Move magic strings/numbers to config:
- Enemy threat thresholds
- Health percentages
- Item type keywords
- Message patterns

---

## CONCLUSION

The codebase has significant opportunities for simplification through careful abstraction and library creation. The proposed changes would:

- **Reduce code by ~1400 lines** (~40% reduction)
- **Improve maintainability** through consistent patterns
- **Increase testability** with isolated modules
- **Enhance readability** with declarative approaches
- **Enable faster feature additions** through standard interfaces

**Recommended approach**: Implement Phase 1 first to gain quick wins, then incrementally add Phase 2 and 3 features as time permits.
