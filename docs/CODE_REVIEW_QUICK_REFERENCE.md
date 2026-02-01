# Code Review Quick Reference Card

## One-Page Cheat Sheet for Refactoring Opportunities

### 🎯 The Big Picture

**Current State**: 2500 lines of code, duplicated logic, 15% code duplication

**Goal**: Reduce to ~1100 lines, eliminate duplication, improve maintainability

**Timeline**: 4 weeks, 4 phases, 18 hours total effort

---

## 🚀 Top 3 Quick Wins (Start Here)

### 1. ANSIHandler (30 min)
```python
# OLD: Repeated in 2+ files
re.sub(r'\x1b\[[^\x1b]*?[a-zA-Z]|\x1b\([B0UK]', '', text)

# NEW: Single utility
ANSIHandler.strip(text)
```

### 2. CachedLayoutParser (30 min)
```python
# OLD: New parser each time
tui_parser = DCSSLayoutParser()
areas = tui_parser.parse_layout(screen)

# NEW: Cached
areas = cached_parser.parse(screen)  # 2nd call is instant
```

### 3. PatternLibrary (1.5 hrs)
```python
# OLD: Inline regex
patterns = [r'Health[:\s]+(\d+)/(\d+)', r'HP[:\s]+(\d+)/(\d+)']

# NEW: Centralized
pattern = PatternLibrary.get('health')
```

---

## 💡 The Major Refactor (Biggest Payoff)

### DecisionEngine - Replace 1200-line method

**Current Structure** (bot.py, _decide_action):
```python
if equip_slot:
    # 20 lines
if quaff_slot:
    # 20 lines
if enemy_detected:
    # 40 lines
if in_shop:
    # 15 lines
# ... 30+ more if/elif blocks covering 1200 lines
return 'o'  # Default
```

**New Structure** (DecisionEngine):
```python
rules = [
    Rule("equip", 10, equip_condition, equip_action),
    Rule("combat", 20, combat_condition, combat_action),
    Rule("shop", 30, shop_condition, shop_action),
    # ... more rules
    Rule("explore", 1000, lambda x: True, explore_action),
]
return engine.decide(context)  # Evaluates rules in priority order
```

**Impact**: 1200 lines → 50 lines, -96% reduction

---

## 📊 Refactoring Roadmap

```
WEEK 1: Phase 1 (Quick Wins)
├─ ANSIHandler ..................... ✓
├─ CachedLayoutParser .............. ✓
├─ PatternLibrary .................. ✓
└─ Create parsers/ package ......... ✓
   Time: 3.5 hrs | Savings: 65 lines | Tests: +5

WEEK 2: Phase 2 (Consolidation)
├─ TextExtractor ................... ✓
├─ ScreenDetector .................. ✓
├─ ActivityLogger .................. ✓
└─ Add tests ...................... ✓
   Time: 7.5 hrs | Savings: 170 lines | Tests: +15

WEEK 3: Phase 3 (Major Refactor)
├─ DecisionEngine .................. ⚠️ (HIGH RISK)
├─ Split bot.py structure ......... ⚠️ (HIGH RISK)
└─ Add comprehensive tests ........ ✓
   Time: 12.5 hrs | Savings: 1100 lines | Tests: +25

WEEK 4: Phase 4 (Polish)
├─ MessageInterpreter ............. ✓
├─ InventoryManager ............... ✓
├─ Config module .................. ✓
└─ Documentation .................. ✓
   Time: 7 hrs | Savings: 110 lines | Tests: +8
```

---

## 📦 Proposed Package Structure

```
crawl_navigator/
├── parsers/
│   ├── ansi_utils.py ............. NEW (Consolidate ANSI handling)
│   ├── pattern_library.py ........ NEW (Centralize regex)
│   ├── text_extractors.py ........ NEW (Unified text extraction)
│   ├── cached_layout.py .......... NEW (Cache layout parsing)
│   ├── message_interpreter.py .... NEW (Interpret game messages)
│   ├── game_state.py ............ MOVE (Existing)
│   └── tui.py .................... MOVE (Existing)
│
├── bot/
│   ├── core.py ................... NEW (Main game loop)
│   ├── combat.py ................. NEW (Combat logic)
│   ├── exploration.py ............ NEW (Exploration logic)
│   ├── inventory.py .............. NEW (Item management)
│   ├── startup.py ................ NEW (Character creation)
│   ├── decision_engine.py ........ NEW (Action decisions)
│   └── activity_logger.py ........ NEW (Logging)
│
├── systems/
│   └── inventory_manager.py ...... NEW (Unified inventory)
│
├── config/
│   └── game_constants.py ......... NEW (Magic numbers/strings)
│
└── main.py (unchanged)
```

---

## 🎲 Risk vs Reward

| Refactoring | Risk | Reward | Priority |
|-------------|------|--------|----------|
| ANSIHandler | ✓✓✓ LOW | ✓✓ MED | 🔴 HIGH |
| CachedLayoutParser | ✓✓✓ LOW | ✓✓ MED | 🔴 HIGH |
| PatternLibrary | ✓✓✓ LOW | ✓✓ MED | 🔴 HIGH |
| TextExtractor | ✓✓ MED | ✓✓✓ HIGH | 🟡 MEDIUM |
| ScreenDetector | ✓✓ MED | ✓✓✓ HIGH | 🟡 MEDIUM |
| DecisionEngine | ✓ HIGH | ✓✓✓✓ VERY HIGH | 🟡 MEDIUM |
| InventoryManager | ✓✓ MED | ✓✓✓ HIGH | 🟡 MEDIUM |

---

## ✅ Success Criteria

### Before This Work
- Lines: ~2500 in bot.py
- Tests: 146 passing
- Coverage: 95%
- Duplication: 15%

### After This Work
- Lines: ~1100 in main files ✓
- Tests: 210+ passing ✓
- Coverage: ≥95% ✓
- Duplication: <5% ✓

---

## 🔍 Code Metrics Improvement

```
LINES OF CODE:     2500 ▓▓▓▓▓▓▓░░░ 1100 (-56%)
DUPLICATION:       15%  ▓▓▓░░░░░░░░░  5% (-67%)
COMPLEXITY:        HIGH ▓▓▓▓▓░░░░░░░ LOW (-50%)
TEST COVERAGE:     95%  ▓▓▓▓▓▓▓▓▓▓░░ 98% (+3%)
MAINTAINABILITY:   OK   ▓▓▓▓░░░░░░░░ GREAT (+60%)
```

---

## 📚 Reference Documents

| Document | Purpose | Length |
|----------|---------|--------|
| CODE_REVIEW_REFACTORING.md | Detailed analysis of all 9 opportunities | 12 pages |
| REFACTORING_CHECKLIST.md | Actionable checklist with priority | 8 pages |
| REFACTORING_EXAMPLES.md | Before/after code examples | 10 pages |
| CODE_REVIEW_SUMMARY.md | Executive summary + strategy | 6 pages |
| **THIS FILE** | Quick reference card | 2 pages |

---

## 🎬 Getting Started

### Option A: Quick Win Approach (Recommended)
1. Start with Phase 1 (3.5 hours)
2. Gain momentum and confidence
3. Incrementally add Phase 2, 3, 4

### Option B: Big Bang Approach
1. Implement all 4 phases at once
2. Complete refactor in 1-2 weeks
3. Higher risk, higher reward

### Option C: Targeted Approach
1. Identify ONE pain point
2. Fix that specific area first
3. Expand based on success

---

## 💻 Development Workflow

```bash
# Phase 1: Quick Wins
git checkout -b refactor/phase-1-utilities
# ... implement ANSIHandler, CachedLayoutParser, PatternLibrary
pytest tests/ -v  # All 146+ tests pass
git commit -am "Phase 1: Utility consolidation"
git push origin refactor/phase-1-utilities

# Phase 2: Consolidation
git checkout -b refactor/phase-2-consolidation
# ... implement TextExtractor, ScreenDetector, ActivityLogger
pytest tests/ -v  # 210+ tests pass
git commit -am "Phase 2: Parsing consolidation"

# Phase 3: Major Refactor
git checkout -b refactor/phase-3-decision-engine
# ... implement DecisionEngine, split bot.py
pytest tests/ -v  # All tests pass
git commit -am "Phase 3: Decision engine refactor"

# Phase 4: Polish
git checkout -b refactor/phase-4-polish
# ... implement MessageInterpreter, InventoryManager, config
pytest tests/ -v  # 220+ tests pass
git commit -am "Phase 4: Polish and finalization"
```

---

## ⚡ Implementation Checklist

### PRE-REFACTORING
- [ ] Read all 3 detailed reference documents
- [ ] Backup current code (git branch)
- [ ] Run full test suite (baseline)
- [ ] Identify stakeholders/reviewers

### PHASE 1
- [ ] Create parsers/ package structure
- [ ] Implement ANSIHandler
- [ ] Implement CachedLayoutParser
- [ ] Implement PatternLibrary core
- [ ] Migrate patterns gradually
- [ ] Add 5 new tests
- [ ] All 146 tests passing
- [ ] Merge to main

### PHASE 2
- [ ] Implement TextExtractor
- [ ] Implement ScreenDetector
- [ ] Implement ActivityLogger
- [ ] Add 15 new tests
- [ ] Update 3 modules to use new utilities
- [ ] All 160+ tests passing
- [ ] Merge to main

### PHASE 3
- [ ] Implement DecisionEngine
- [ ] Add 25+ new tests (comprehensive!)
- [ ] Refactor _decide_action() to use engine
- [ ] Split bot.py into modules (optional)
- [ ] All 185+ tests passing
- [ ] Performance validation
- [ ] Code review (2+ reviewers)
- [ ] Merge to main

### PHASE 4
- [ ] Implement MessageInterpreter
- [ ] Implement InventoryManager
- [ ] Create config/ module
- [ ] Add 8 new tests
- [ ] Documentation updates
- [ ] Final test suite validation (210+ tests)
- [ ] Merge to main

### POST-REFACTORING
- [ ] 100+ step game runs (validation)
- [ ] Update DEVELOPER_GUIDE.md
- [ ] Update ARCHITECTURE.md
- [ ] Performance benchmarking
- [ ] Final metrics review

---

## 🎓 Key Takeaways

1. **Start small** - Phase 1 gives quick confidence boost
2. **One at a time** - Don't refactor multiple areas simultaneously
3. **Test thoroughly** - Each phase needs comprehensive tests
4. **Document as you go** - Update docs with each phase
5. **Validate constantly** - Run game after each change
6. **Get feedback early** - Share Phase 1 results for review

---

## 📞 Questions Before Starting?

- What's your risk tolerance?
- Is 18 hours over 4 weeks realistic?
- Should we start with Phase 1 or jump to DecisionEngine?
- Who will review code changes?
- When should this work happen (sprint planning)?

---

**Document Version**: 1.0  
**Last Updated**: January 31, 2026  
**Status**: Ready for Implementation
