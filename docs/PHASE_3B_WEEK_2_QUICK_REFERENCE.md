# Phase 3b Week 2: Combat & Health Testing - Quick Reference

## Test Execution

Run all 23 combat decision tests:
```bash
cd /home/skahler/workspace/crawl_navigator
source venv/bin/activate
pytest tests/test_combat_decisions.py -v
```

Expected output:
```
tests/test_combat_decisions.py ....................... 23 PASSED
```

Run full test suite to check for regressions:
```bash
pytest tests/ -q
```

Expected output:
```
======================== 216 passed in 27.29s =========================
```

## Test Structure

### File Location
- `tests/test_combat_decisions.py` (500+ lines, 23 tests)

### Helper Function
```python
def create_test_context(**kwargs):
    """Create properly initialized test context matching DecisionContext."""
    # Returns object with:
    # - All fields initialized to safe defaults
    # - @property health_percentage for accurate calculations
    # - Kwargs override for scenario-specific values
```

### Test Classes (8 total)
1. **TestCombatDetection** (4 tests) - Enemy detection and autofight triggering
2. **TestHealthBasedDecisions** (4 tests) - Health-based rest vs explore
3. **TestCombatSequences** (2 tests) - Combat flow and recovery cycles
4. **TestPromptPriorityOverCombat** (2 tests) - Prompt handling priority
5. **TestHealthThresholds** (3 tests) - Specific health % boundaries
6. **TestCombatWithVariousEnemies** (5 tests) - Enemy type variety
7. **TestEdgeCases** (3 tests) - Boundary conditions
8. **TestEdgeCases** (continuation) - Additional edge cases

## DecisionEngine Command Reference

| Command | ASCII | Priority | Condition | Usage |
|---------|-------|----------|-----------|-------|
| ' ' | Space | CRITICAL | `has_more_prompt` | Respond to more prompts |
| 'S' | S key | CRITICAL | `has_level_up` | Accept level-up |
| '\t' | Tab | NORMAL | `enemy_detected and health_percentage > 70` | Autofight |
| '5' | 5 key | NORMAL | `has_gameplay_indicators and health_percentage < 60` | Rest to recover |
| '.' | Period | NORMAL | `last_action_sent == '\t' and not enemy_detected` | Wait after combat |
| 'o' | o key | NORMAL | `has_gameplay_indicators and health_percentage >= 60` | Auto-explore |
| '' | Empty | NORMAL | `enemy_detected and health_percentage <= 70` | Combat movement |

## Key Test Scenarios

### Combat Detection (4 tests)
- **Good Health (80%)**: Engine autofights ('\t') with enemy
- **Low Health (15%)**: Engine doesn't autofight with enemy
- **No Enemy**: Engine explores ('o')
- **Multiple Enemies**: Engine still autofights

### Health-Based Decisions (4 tests)
- **Very Low (10%)**: Engine rests ('5')
- **Good Health (85%)**: Engine explores ('o')
- **Medium Health (50%)**: Engine makes valid decision
- **Low Health Priority**: Engine prioritizes rest over exploration

### Health Thresholds (3 tests)
- **30% Health**: Rest decision
- **60% Health**: Transition zone (can explore or rest)
- **80% Health**: Explore decision

### Combat Sequences (2 tests)
- **Autofight Flow**: Enemy → autofight ('\t') → wait ('.')
- **Recovery Cycle**: Damaged → rest ('5') → recovering → explored ('o')

### Edge Cases (3 tests)
- **0% Health**: No crash, valid action returned
- **100% Health**: Explores ('o')
- **Zero Max Health**: Handled gracefully

## Context Property Values

All context properties for testing:

```python
create_test_context(
    # Combat state
    enemy_detected=True/False,
    enemy_name="bat",  # or any creature name
    
    # Health state
    health=80,         # current HP
    max_health=100,    # max HP
    # health_percentage calculated as @property: (health/max_health)*100
    
    # Prompt flags
    has_more_prompt=False,
    has_equip_slot_prompt=False,
    has_quaff_slot_prompt=False,
    has_level_up=False,
    attribute_increase_prompt=False,
    save_game_prompt=False,
    
    # Menu state
    in_shop=False,
    in_inventory_screen=False,
    in_item_pickup_menu=False,
    in_menu=False,
    
    # Gameplay indicators
    has_gameplay_indicators=True,
    gameplay_started=True,
    
    # Movement/action
    last_action_sent="",  # previous command sent
    
    # Other state
    items_on_ground=False,
    equip_slot_pending=False,
    quaff_slot_pending=False,
    level=1,
    dungeon_level=1,
    output="",  # raw screen output
)
```

## Test Naming Conventions

All tests follow pattern: `test_{scenario}_{aspect}`

Examples:
- `test_autofight_with_good_health` - Scenario: combat with good health, Aspect: autofight behavior
- `test_health_priority_over_exploration` - Scenario: low health, Aspect: priority ordering
- `test_health_recovery_cycle` - Scenario: full recovery sequence, Aspect: state transitions

## Common Assertions

```python
# Command assertions
assert command == '\t'           # Autofight
assert command == '5'            # Rest
assert command == '.'            # Wait
assert command == 'o'            # Explore
assert command == ' '            # More prompt response
assert command in ['o', '5', '.']  # Valid choices

# Reason assertions
assert 'autofight' in reason.lower()
assert 'combat' in reason.lower()
assert 'health' in reason.lower()

# Non-null assertions
assert command is not None
assert reason is not None
```

## Test Execution Examples

### Run specific test class:
```bash
pytest tests/test_combat_decisions.py::TestCombatDetection -v
```

### Run specific test method:
```bash
pytest tests/test_combat_decisions.py::TestCombatDetection::test_autofight_with_good_health -v
```

### Run with detailed output:
```bash
pytest tests/test_combat_decisions.py -v -s
```

### Run with coverage:
```bash
pytest tests/test_combat_decisions.py --cov=decision_engine --cov-report=term-missing
```

## Pass/Fail Status

Current Status: **✅ ALL PASSING (23/23)**

- TestCombatDetection: 4/4 ✅
- TestHealthBasedDecisions: 4/4 ✅
- TestCombatSequences: 2/2 ✅
- TestPromptPriorityOverCombat: 2/2 ✅
- TestHealthThresholds: 3/3 ✅
- TestCombatWithVariousEnemies: 5/5 ✅
- TestEdgeCases: 3/3 ✅

Overall Test Suite: **✅ 216/216 PASSING**
- 0 regressions
- 0 failures
- 100% pass rate

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total Test Time | 7.38 seconds |
| Average per test | ~320ms |
| Slowest test | < 1 second |
| Fastest test | < 100ms |
| Memory overhead | < 50MB |

## Troubleshooting

### Issue: MagicMock comparison errors
**Solution**: Use `create_test_context()` helper, not raw MagicMock

### Issue: Tests return '' or wrong command
**Solution**: Verify context fields are properly initialized with correct boolean values

### Issue: health_percentage not working
**Solution**: Ensure max_health > 0 (defaults to 100 if not specified)

### Issue: Test hanging
**Solution**: Check for infinite loops in rule conditions or action lambdas

## Debugging Tips

Enable verbose output:
```bash
pytest tests/test_combat_decisions.py -v -s --log-cli-level=DEBUG
```

Print context values in test:
```python
context = create_test_context(enemy_detected=True, health=80, max_health=100)
print(f"Context health: {context.health}")
print(f"Context health_percentage: {context.health_percentage}")
```

Check engine decision:
```python
command, reason = bot.decision_engine.decide(context)
print(f"Decision: {repr(command)}")
print(f"Reason: {reason}")
```

## Related Files

- **Engine Implementation**: `decision_engine.py` (364 lines)
- **Engine Integration**: `bot.py` lines 770-880 (decision_engine.decide() call)
- **Phase 3b Wrapper Tests**: `tests/test_phase_3b_wrapper.py`
- **Phase 3a Tests**: `tests/test_decision_engine.py` (22 tests)
- **Integration Tests**: `tests/test_decision_engine_integration.py` (10 tests)

## Success Criteria (Met ✅)

- [x] Create 20+ combat decision tests
- [x] Achieve 100% pass rate
- [x] Cover all health thresholds
- [x] Test combat sequences
- [x] Validate prompt priorities
- [x] Handle edge cases
- [x] Zero regressions on full suite
- [x] Complete documentation

**Phase 3b Week 2: COMPLETE** ✅
