# Phase 3b Migration Guide: Integrating DecisionEngine into _decide_action

## Overview

This guide describes how to incrementally migrate the existing `_decide_action()` method to use the DecisionEngine. The goal is to gradually replace 1200+ lines of nested if/elif logic with rule-based decisions.

## Migration Strategy

### Why Incremental?
- **Safety**: Each migration step can be tested independently
- **Reversibility**: Easy to revert if issues occur
- **Learning**: Validates engine behavior before full cutover
- **Risk Management**: Slow rollout catches edge cases early

### Phase 3b Timeline (Recommended)

```
Week 1: Quick Wins (High-Confidence Rules)
  └─ Menu prompts (equip, quaff, save game, more)
  └─ Shop detection
  └─ Time: 1-2 hours

Week 2: Combat & Health
  └─ Combat decisions (autofight vs movement)
  └─ Health-based rest vs explore
  └─ Time: 2-3 hours

Week 3: Complex Logic
  └─ Level-up handling
  └─ Inventory management
  └─ Goto sequences
  └─ Time: 2-3 hours

Week 4: Consolidation
  └─ Remove old code
  └─ Performance testing
  └─ Documentation updates
  └─ Time: 1-2 hours

Total: ~8-10 hours
```

## Implementation Steps

### Step 1: Create Decision Categories

The `_decide_action()` method has several conceptual categories. Let's organize them:

```python
# Current order in _decide_action():
1. Equip slot prompt (CRITICAL)
2. Quaff slot prompt (CRITICAL)
3. Attribute increase prompt (CRITICAL)
4. Save game prompt (CRITICAL)
5. Level-up message (URGENT)
6. More prompt (CRITICAL)
7. Shop interface (HIGH)
8. Item pickup menu (HIGH)
9. Inventory screen (HIGH)
10. Better armor detection (URGENT)
11. Untested potions (URGENT)
12. Combat with enemy (NORMAL)
13. Health-based decisions (NORMAL)
14. Goto sequence (NORMAL)
```

### Step 2: Verify Engine Rules Match

Check that `create_default_engine()` already has rules for all categories:

```python
engine = create_default_engine()
print(f"Engine has {len(engine.rules)} rules")

for rule in sorted(engine.rules, key=lambda r: r.priority.value):
    print(f"  {rule.priority.name:8} {rule.name}")
```

Expected output: ~20 rules covering all categories

### Step 3: Create Wrapper Method

Before modifying `_decide_action()`, create a wrapper that uses the engine:

```python
def _decide_action_using_engine(self, output: str) -> Optional[str]:
    """
    NEW IMPLEMENTATION: Use DecisionEngine for action decisions.
    
    This method will gradually replace the old _decide_action() logic.
    Currently evaluates critical and high-priority rules first.
    Falls back to old logic for unhandled cases.
    """
    try:
        # Prepare game state context
        context = self._prepare_decision_context(output)
        
        # Evaluate engine rules
        command, reason = self.decision_engine.decide(context)
        
        if command is not None:
            return self._return_action(command, reason)
        
    except Exception as e:
        logger.error(f"Error in DecisionEngine: {e}")
        logger.debug(traceback.format_exc())
    
    # Fallback: use old logic
    return self._decide_action_legacy(output)

def _decide_action(self, output: str) -> Optional[str]:
    """Public interface - routes to appropriate implementation."""
    # Feature flag to gradually migrate
    if self.use_decision_engine:
        return self._decide_action_using_engine(output)
    else:
        return self._decide_action_legacy(output)
```

### Step 4: Rename Current Implementation

Make a backup of the current `_decide_action()`:

```python
# In bot.py __init__(), add:
self.use_decision_engine = False  # Feature flag for gradual rollout

# Rename current method:
def _decide_action_legacy(self, output: str) -> Optional[str]:
    """DEPRECATED: Original nested if/elif logic.
    
    This is the v1.7 implementation. Being replaced by DecisionEngine (v1.8+).
    Kept for fallback during migration (Phase 3b).
    
    TODO: Remove after DecisionEngine fully tested and migrated.
    """
    # ... existing 1200+ lines of code unchanged ...
```

### Step 5: Test Both Implementations in Parallel

Create test comparing old vs new behavior:

```python
def test_engine_vs_legacy_compatibility():
    """Verify DecisionEngine makes same decisions as legacy for known scenarios."""
    bot = DCSSBot()
    screen_text = "... game screen text ..."
    
    # Test with legacy
    bot.use_decision_engine = False
    cmd_legacy, _ = bot._decide_action(screen_text), bot.action_reason
    
    # Test with engine
    bot.use_decision_engine = True
    cmd_engine, _ = bot._decide_action(screen_text), bot.action_reason
    
    # Should be same or compatible
    assert cmd_legacy == cmd_engine or cmd_engine is not None
```

### Step 6: Enable Engine with Feature Flag

Add to `main.py`:

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--use-engine', action='store_true',
                    help='Use DecisionEngine for decisions (Phase 3b)')
args = parser.parse_args()

bot = DCSSBot(crawl_command=args.crawl_cmd)
bot.use_decision_engine = args.use_engine  # Enable via flag

# Run with: python main.py --steps 100 --use-engine
```

### Step 7: Incremental Migration Process

**Week 1: Menu Prompts & Shop**

Identify these lines in `_decide_action_legacy()`:
```python
# Lines ~1500-1530: Menu prompt handling
if self.equip_slot:
    # ...
elif self.quaff_slot:
    # ...
elif '--more--' in output:
    # ...

# Lines ~1580-1585: Shop detection
if self._is_in_shop(output):
    # ...
```

Move this logic to a separate method (for clarity during migration):

```python
def _should_use_engine_for_critical(self) -> bool:
    """Phase 3b: Use engine for critical priorities."""
    return self.migration_phase >= 1

def _decide_action_phase_1(self, output: str) -> Optional[str]:
    """PHASE 1 MIGRATION: Menu prompts & shop.
    
    Tests: test_decision_engine_integration.py
    """
    context = self._prepare_decision_context(output)
    
    # Check CRITICAL rules only
    for rule in self.decision_engine.rules:
        if rule.priority.value <= 1:  # CRITICAL
            if rule.condition(context):
                cmd, reason = rule.action(context)
                if cmd is not None:
                    return self._return_action(cmd, reason)
    
    # Fall back to legacy
    return self._decide_action_legacy(output)
```

**Week 2: Combat & Health**

Add HIGH and URGENT rules:

```python
def _decide_action_phase_2(self, output: str) -> Optional[str]:
    """PHASE 2 MIGRATION: Combat & health decisions.
    
    Tests: test_combat_sequence_scenario(), test_exploration_health_management()
    """
    context = self._prepare_decision_context(output)
    
    # Evaluate all rules except LOW priority
    for rule in sorted(self.decision_engine.rules, key=lambda r: r.priority.value):
        if rule.priority.value >= 30:  # Skip LOW
            continue
        if rule.condition(context):
            cmd, reason = rule.action(context)
            if cmd is not None:
                return self._return_action(cmd, reason)
    
    # Fall back to legacy
    return self._decide_action_legacy(output)
```

**Week 3: Full Engine**

```python
def _decide_action_engine_full(self, output: str) -> Optional[str]:
    """PHASE 3 MIGRATION: Full DecisionEngine adoption.
    
    Uses engine for all decisions. Legacy fallback only for emergencies.
    """
    context = self._prepare_decision_context(output)
    command, reason = self.decision_engine.decide(context)
    
    if command is not None:
        return self._return_action(command, reason)
    
    # Final fallback (shouldn't reach here)
    logger.warning("Engine returned no decision, using legacy fallback")
    return self._decide_action_legacy(output)
```

### Step 8: Validation Testing

For each phase, run:

```bash
# Test menu prompts & shop
python main.py --steps 50 --use-engine
# Verify: No unexpected equip/quaff prompts, shop exits immediately

# Test combat
python main.py --steps 100 --use-engine
# Verify: Autofight works, health-based rest works

# Test full game
python main.py --steps 500 --use-engine
# Verify: Full playthrough works, reaches deeper levels

# Compare performance
python main.py --steps 100 --no-engine
time python main.py --steps 100 --use-engine
# Verify: No significant slowdown
```

## Risk Mitigation

### 1. Feature Flag Strategy

```python
class DecisionMigration(Enum):
    LEGACY_ONLY = 0       # Original implementation
    PHASE_1_CRITICAL = 1  # Menu + shop
    PHASE_2_COMBAT = 2    # Combat + health
    PHASE_3_FULL = 3      # Full engine
    ENGINE_ONLY = 4       # Legacy removed

bot.migration_phase = DecisionMigration.PHASE_1_CRITICAL
```

### 2. Logging & Monitoring

```python
def _log_decision_comparison(self, legacy_cmd, engine_cmd, output):
    """Log when engine makes different decision than legacy."""
    if legacy_cmd != engine_cmd:
        logger.warning(f"Decision divergence: legacy={legacy_cmd}, engine={engine_cmd}")
        logger.debug(f"Output: {output[:100]}...")
```

### 3. Regression Testing

```python
@pytest.mark.parametrize("phase", [
    DecisionMigration.LEGACY_ONLY,
    DecisionMigration.PHASE_1_CRITICAL,
    DecisionMigration.PHASE_2_COMBAT,
    DecisionMigration.PHASE_3_FULL,
])
def test_all_phases(phase):
    """Regression test: each migration phase must pass."""
    bot.migration_phase = phase
    # Run 100-step game test
    # Verify: No crashes, progress made
```

## Monitoring During Migration

### Key Metrics

```python
class MigrationMetrics:
    move_count: int = 0
    engine_decisions: int = 0
    legacy_fallbacks: int = 0
    decision_divergences: int = 0
    game_over_level: int = 0
    
    @property
    def engine_usage_percent(self) -> float:
        total = self.engine_decisions + self.legacy_fallbacks
        return (self.engine_decisions / total * 100) if total > 0 else 0

# Log at end of game
logger.info(f"Migration: {metrics.engine_usage_percent:.1f}% using engine, "
            f"{metrics.decision_divergences} divergences, "
            f"reached level {metrics.game_over_level}")
```

### Monitoring Queries

```python
# Check engine adoption rate
grep "Engine decisions:" logs/bot_session_*.log | tail -10

# Find divergence points
grep "Decision divergence" logs/bot_session_*.log

# Compare game depth by phase
for phase in LEGACY PHASE_1 PHASE_2 PHASE_3; do
    grep "reached level" logs/*_$phase.log | avg
done
```

## Success Criteria

| Milestone | Criteria | Timeline |
|-----------|----------|----------|
| Phase 1 | 90%+ same decisions as legacy | 1 week |
| Phase 2 | 100 step games without crashes | 1 week |
| Phase 3 | 500 step games without crashes | 1 week |
| Full | Legacy code removed, engine only | 1 week |

## Rollback Plan

If issues detected at any phase:

```
1. Immediate: Set migration_phase = LEGACY_ONLY
2. Investigate: Compare engine vs legacy decisions
3. Fix: Add specific rule or adjust existing rule
4. Test: Unit tests for specific scenario
5. Re-enable: Gradually increase migration_phase again
```

## Documentation Updates

After each phase, update:

- `CHANGELOG.md` - New phase milestone
- `ARCHITECTURE.md` - Engine integration progress
- `DEVELOPER_GUIDE.md` - New patterns and examples
- `DECISION_ENGINE_QUICK_REFERENCE.md` - Usage examples

## Success Example

After Phase 3b, expected result:

```python
# Before (1200+ lines)
def _decide_action(self, output):
    if self.equip_slot:
        ...
    elif self.quaff_slot:
        ...
    # ... 30+ more elif blocks
    return 'o'

# After (50 lines)
def _decide_action(self, output):
    context = self._prepare_decision_context(output)
    command, reason = self.decision_engine.decide(context)
    if command is not None:
        return self._return_action(command, reason)
    # Emergency fallback (shouldn't reach)
    return self._return_action('o', "Fallback: auto-explore")
```

### Metrics Improvement

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| _decide_action() | 1200 lines | 50 lines | 1150 lines |
| Total bot.py | 2500 lines | 1350 lines | 1150 lines |
| Cyclomatic complexity | 120+ | 5 | -96% |
| Test coverage | 75% | 95%+ | +20% |
| Time to add new rule | 30 min | 5 min | -83% |

## Next Steps (Phase 3c+)

After Phase 3b completes:

1. **Rule Categorization**: Separate engine rules by domain
   - `combat_rules.py`
   - `exploration_rules.py`
   - `inventory_rules.py`
   - `prompt_rules.py`

2. **Performance Optimization**: Cache context, parallel evaluation

3. **Advanced Features**: Rule composition, conditional rules, weighted priorities

4. **Machine Learning**: Learn optimal rule ordering from gameplay data

---

**Status**: Phase 3b migration guide ready
**Target Completion**: 2-3 weeks
**Expected Outcome**: 50%+ code complexity reduction
