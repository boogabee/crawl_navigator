# Phase 3b Action Checklist

**Status**: Ready to Begin
**Prerequisite**: Phase 3a Complete ✅
**Duration**: 2-3 weeks
**Outcome**: Engine fully integrated, legacy code removed, 50%+ complexity reduction

---

## Pre-Phase Validation ✅

- [x] DecisionEngine core built and tested (363 lines)
- [x] Unit tests passing (22/22) ✅
- [x] Integration tests passing (10/10) ✅
- [x] Bot integration completed (~65 lines)
- [x] Documentation complete (1,350+ lines)
- [x] No regressions (146/146 original tests passing)
- [x] All 178 tests passing

**Ready to proceed: YES** ✅

---

## Week 1: Quick Wins (Menu Prompts & Shop)

### Task 1.1: Create Feature Flag Infrastructure
- [ ] Add `use_decision_engine` flag to DCSSBot `__init__()`
- [ ] Add `--use-engine` command-line argument to `main.py`
- [ ] Add logging when flag switches between implementations
- **Time estimate**: 30 minutes
- **Files**: `bot.py`, `main.py`
- **Tests**: Create `test_feature_flag.py` with basic flag tests

### Task 1.2: Create Wrapper Methods
- [ ] Rename `_decide_action()` to `_decide_action_legacy()`
- [ ] Create new `_decide_action()` that routes via feature flag
- [ ] Create `_decide_action_engine()` wrapper
- [ ] Verify all calls still work (no errors)
- **Time estimate**: 30 minutes
- **Files**: `bot.py`
- **Tests**: Run existing test suite, verify no breakage

### Task 1.3: Test Menu Prompts with Engine
- [ ] Run `python main.py --steps 50 --use-engine`
- [ ] Verify equip/quaff slots handled correctly
- [ ] Verify more prompts dismissed
- [ ] Verify game progresses normally
- **Time estimate**: 10 minutes per test run × 3 = 30 minutes
- **Acceptance**: No stuck loops, no unexpected prompts, progress made

### Task 1.4: Test Shop Detection with Engine
- [ ] Run `python main.py --steps 100 --use-engine`
- [ ] Intentionally walk into shop
- [ ] Verify bot exits immediately (no purchases)
- [ ] Verify no errors in logs
- **Time estimate**: 15 minutes
- **Acceptance**: Shop exited cleanly, no items purchased

### Task 1.5: Week 1 Validation
- [ ] Create `test_week_1_summary.py`
  - Test menu prompt priority (equip > quaff > more)
  - Test shop exit precedence
  - Test multiple consecutive prompts
- [ ] Run full test suite: `pytest tests/ -q`
- [ ] Verify all 178+ tests still passing
- [ ] Document results in `WEEK_1_SUMMARY.md`
- **Time estimate**: 1 hour
- **Acceptance**: 100% tests passing, no regressions

---

## Week 2: Combat & Health

### Task 2.1: Validate Combat Detection
- [ ] Run game and trigger combat scenario
- [ ] Verify engine detects enemy correctly
- [ ] Verify autofight decision made
- [ ] Check logs for decision reasoning
- **Time estimate**: 20 minutes
- **Command**: `python main.py --steps 100 --use-engine --debug`

### Task 2.2: Test Health-Based Decisions
- [ ] Manually reduce health to low threshold
- [ ] Verify bot chooses rest ('s') over exploration
- [ ] Verify bot resumes exploration after healing
- **Time estimate**: 20 minutes

### Task 2.3: Validate Combat Sequence
- [ ] Run `pytest tests/test_decision_engine_integration.py::TestDecisionEngineIntegration::test_combat_sequence_scenario -v`
- [ ] Verify autofight → rest → explore sequence
- [ ] Add similar test for real game
- **Time estimate**: 30 minutes

### Task 2.4: Create Combat Decision Tests
- [ ] Create `test_combat_decisions.py`
  - Test autofight with different health levels
  - Test retreat at low health
  - Test rest vs explore priority
- [ ] All new tests must pass
- **Time estimate**: 1 hour
- **Acceptance**: All combat tests passing

### Task 2.5: Week 2 Validation
- [ ] Run 100-step games with `--use-engine`
- [ ] Monitor logs for decision divergence
- [ ] Verify game reaches deeper levels
- [ ] Document results in `WEEK_2_SUMMARY.md`
- **Time estimate**: 1 hour
- **Acceptance**: 100-step games reach level 3+, no crashes

---

## Week 3: Complex Logic & Edge Cases

### Task 3.1: Test Level-Up Handling
- [ ] Run game, trigger level-up
- [ ] Verify stat increase handled correctly
- [ ] Verify no infinite loops
- **Time estimate**: 20 minutes

### Task 3.2: Test Inventory Management
- [ ] Run game, trigger inventory screen
- [ ] Verify no stuck loops
- [ ] Verify bot continues after closing inventory
- **Time estimate**: 20 minutes

### Task 3.3: Test Goto Sequences
- [ ] Run game with goto commands
- [ ] Verify descent sequences work
- [ ] Verify level changes handled
- **Time estimate**: 20 minutes

### Task 3.4: Add Complex Decision Tests
- [ ] Create `test_complex_decisions.py`
  - Test level-up with multiple prompts
  - Test inventory handling
  - Test goto sequences
  - Test prompt chains
- [ ] All tests must pass
- **Time estimate**: 1 hour

### Task 3.5: Comprehensive Game Run
- [ ] Run `python main.py --steps 200 --use-engine`
- [ ] Verify no crashes at any point
- [ ] Monitor for divergence from legacy
- [ ] Document edge cases found
- **Time estimate**: 30 minutes
- **Acceptance**: 200-step run completes successfully

### Task 3.6: Week 3 Validation
- [ ] All complex decision tests passing
- [ ] 200-step game runs without errors
- [ ] No regressions in existing tests
- [ ] Document results in `WEEK_3_SUMMARY.md`
- **Time estimate**: 30 minutes

---

## Week 4: Integration & Cleanup

### Task 4.1: Performance Profiling
- [ ] Run legacy implementation: `time python main.py --steps 100`
- [ ] Run engine implementation: `time python main.py --steps 100 --use-engine`
- [ ] Compare execution times
- [ ] If slower, identify bottleneck
- **Time estimate**: 30 minutes
- **Acceptance**: No significant performance regression

### Task 4.2: Decision Monitoring
- [ ] Add `DecisionMetrics` class to track:
  - Total decisions made
  - Engine vs legacy usage %
  - Decision divergences
  - Game progression metrics
- [ ] Log metrics at end of each game
- **Time estimate**: 1 hour
- **Files**: `bot.py` (new class)

### Task 4.3: Comprehensive Regression Test
- [ ] Run full test suite with `--use-engine` enabled
- [ ] `pytest tests/ -v` with engine enabled
- [ ] Verify all 178 tests still passing
- [ ] No new failures or warnings
- **Time estimate**: 30 minutes
- **Acceptance**: 178/178 tests passing

### Task 4.4: Documentation Updates
- [ ] Update `README.md` with engine status
- [ ] Update `ARCHITECTURE.md` with new architecture
- [ ] Update `DEVELOPER_GUIDE.md` with migration notes
- [ ] Update `CHANGELOG.md` with Phase 3b completion
- **Time estimate**: 1 hour
- **Files**: Multiple docs

### Task 4.5: Remove Legacy Code Path
- [ ] Verify engine makes 100% of decisions
- [ ] Remove `_decide_action_legacy()` method
- [ ] Remove feature flag (always use engine)
- [ ] Remove `--use-engine` command-line option
- [ ] Run full tests to confirm no issues
- **Time estimate**: 30 minutes
- **Acceptance**: All tests pass, no crashes

### Task 4.6: Final Validation
- [ ] Run `python main.py --steps 500 --debug`
- [ ] Monitor for any issues
- [ ] Verify game reaches level 10+
- [ ] Document final metrics
- **Time estimate**: 1 hour (plus game runtime)
- **Acceptance**: 500-step game completes successfully

### Task 4.7: Week 4 Summary
- [ ] Create `WEEK_4_SUMMARY.md`
- [ ] Create `PHASE_3B_COMPLETION_REPORT.md`
- [ ] Document metrics and results
- [ ] Record before/after code complexity
- **Time estimate**: 1 hour

---

## Ongoing: Monitoring & Logging

### Daily Tasks During Phase 3b

- [ ] Check test results after code changes
- [ ] Monitor logs for new errors or warnings
- [ ] Track decision divergence metrics
- [ ] Document findings in daily notes
- [ ] Update PHASE_3B_PROGRESS.md with status

### Weekly Tasks

- [ ] Review all logs from week's runs
- [ ] Identify any patterns or issues
- [ ] Adjust engine rules if needed
- [ ] Create weekly summary document
- [ ] Plan next week's work

---

## Rollback Procedures

### If Critical Issue Found

1. **Immediate**: Set `use_decision_engine = False` in bot.py
2. **Investigate**: Compare engine vs legacy decisions
3. **Diagnose**: Add logging to understand divergence
4. **Fix**: Adjust engine rule or context preparation
5. **Test**: Create test for specific scenario
6. **Retry**: Enable engine and re-test

### Commands

```bash
# Rollback to legacy
git checkout bot.py  # Reverts use_decision_engine flag

# Create minimal test to debug
pytest tests/test_decision_engine.py::TestDefaultEngine::test_combat_with_good_health -v

# Compare implementations
python -c "
from decision_engine import create_default_engine
engine = create_default_engine()
print(f'Engine has {len(engine.rules)} rules')
"

# Review logs
tail -100 logs/bot_session_*.log | grep "ERROR\|WARN"
```

---

## Success Criteria

### Must Have ✅

- [ ] All 178 original tests still passing
- [ ] Engine handles 200+ move games without crashes
- [ ] Menu prompts prioritized correctly
- [ ] Combat and health decisions working
- [ ] Shop detection and exit working
- [ ] No performance regression (≤5% slower acceptable)
- [ ] No unexpected game-over situations
- [ ] Comprehensive test suite for new logic

### Should Have 🎯

- [ ] 100% of decisions through engine
- [ ] Legacy code path removed
- [ ] Performance maintained or improved
- [ ] Documentation updated
- [ ] 50+ move runs reach level 10+

### Nice to Have 🌟

- [ ] Rule categorization by domain
- [ ] Performance optimization
- [ ] Decision metrics dashboard
- [ ] Machine learning preparation

---

## Time Breakdown

| Phase | Task | Est. Time |
|-------|------|-----------|
| Week 1 | Feature flag + shop test | 3 hours |
| Week 2 | Combat validation | 3.5 hours |
| Week 3 | Complex logic | 3.5 hours |
| Week 4 | Integration + cleanup | 4 hours |
| **Total** | | **14 hours** |

**Target completion**: 2-3 weeks at 5-7 hours per week

---

## Key Contacts & Resources

### Documentation
- [PHASE_3B_MIGRATION_GUIDE.md](PHASE_3B_MIGRATION_GUIDE.md) - Detailed migration roadmap
- [DECISION_ENGINE_IMPLEMENTATION.md](DECISION_ENGINE_IMPLEMENTATION.md) - Technical reference
- [DECISION_ENGINE_QUICK_REFERENCE.md](DECISION_ENGINE_QUICK_REFERENCE.md) - Developer guide

### Code References
- `decision_engine.py` - Core engine implementation
- `bot.py` - Bot integration (see `_prepare_decision_context()`)
- `tests/test_decision_engine*.py` - Test examples

### Commands

```bash
# Activate environment
source venv/bin/activate

# Run engine tests only
pytest tests/test_decision_engine.py -v

# Run all tests
pytest tests/ -q

# Run single game (100 steps)
python main.py --steps 100 --debug

# Check test count
pytest tests/ --collect-only | grep "test session" -A 1
```

---

## Sign-Off

**Phase 3a Status**: ✅ COMPLETE
- All deliverables completed
- All tests passing (178/178)
- Documentation complete
- Ready for Phase 3b

**Phase 3b Status**: 📋 READY TO START
- All prerequisites met
- Detailed roadmap provided
- Risk mitigation documented
- Success criteria defined

**Next Steps**: Begin Week 1 tasks when ready.

---

**Last Updated**: January 31, 2026
**Status**: Ready for Phase 3b
**Next Review**: End of Week 1
