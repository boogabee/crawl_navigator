# Phase 3b Week 3-4: Full Integration - Migration Plan

**Status**: Starting Phase 3-4  
**Target**: Gradually migrate 769-line `_decide_action_legacy()` to DecisionEngine  
**Goal**: 50%+ code reduction (from 769 to ~380 lines or less)

## Current State Assessment

### Legacy Implementation Size
- **Method**: `_decide_action_legacy()` (lines 1626-2395)
- **Size**: 769 lines
- **Test Coverage**: 136 original + 216 total with new tests
- **Feature Flag**: `use_decision_engine` (default False)

### DecisionEngine Status
- **Core**: 363 lines in `decision_engine.py`
- **Rules**: 24 rules configured and tested
- **Tests**: 42 Phase 3a + 15 Phase 3b Week 1 + 23 Phase 3b Week 2 = 80 dedicated tests
- **Pass Rate**: 100% (216/216 all tests)

## Migration Strategy

### Phase 1: Analysis & Planning (Start of Week 3)
1. **Audit Legacy Code**
   - Map all decision branches in `_decide_action_legacy()`
   - Identify which branches have corresponding engine rules
   - Identify missing rules that need to be added
   - Identify branches that are dead code or can be simplified

2. **Rule Coverage Assessment**
   - Check if DecisionEngine covers all scenarios
   - Identify gaps in rule set
   - Plan new rules if needed

3. **Test Baseline**
   - Run full test suite (216 tests)
   - Run legacy implementation with 50-move game (timeout: 10sec/step = 500sec total)
   - Document baseline behavior

### Phase 2: Incremental Rule Addition (Mid Week 3)
1. **Add Missing Rules** (if any identified)
   - Implement rules for uncovered scenarios
   - Add unit tests for new rules
   - Validate with existing test suite

2. **Rule Refinement**
   - Adjust priority levels if needed
   - Refine condition logic based on real game behavior
   - Optimize rule evaluation

### Phase 3: Gradual Migration (Late Week 3 - Week 4)
1. **Enable Engine for Subset**
   - Run tests with `--use-engine` flag
   - Validate all 216 tests pass
   - Run real game with engine (50-100 moves)

2. **Validate Decision Consistency**
   - Compare engine decisions vs legacy decisions
   - Identify any divergences
   - Adjust rules if needed

3. **Performance Testing**
   - Measure decision latency (engine vs legacy)
   - Profile rule evaluation order
   - Optimize hot paths

### Phase 4: Cleanup & Documentation (End of Week 4)
1. **Code Removal**
   - Remove dead code from `_decide_action_legacy()`
   - Remove legacy helper methods no longer needed
   - Update imports/dependencies

2. **Final Validation**
   - Run extended game test (200-500 moves with engine)
   - Verify all edge cases handled
   - Performance benchmarking

3. **Documentation**
   - Create migration summary
   - Document decisions made
   - Update architecture documentation

## Current DecisionEngine Rules (24 total)

### CRITICAL Priority (Highest)
1. More prompt (respond with space)
2. Level up (respond with S)
3. Equipment slot pending
4. Quaff slot pending
5. Save game prompt
6. Inventory screen detection

### URGENT Priority
7. Attribute increase prompt

### HIGH Priority
8. Combat (low health movement)
9. Combat (autofight)
10. Item pickup menu handling

### NORMAL Priority
11-19. Goto commands and location type selection
20. Rest after autofight
21. Explore with good health
22. Rest to recover

### LOW Priority
23-24. Fallback exploration

## Key Decision Points in Legacy Code

Need to map these to engine rules:

1. **Shop Detection** → Engine rule: "Shop exit" (NORMAL priority)
2. **Level Up Handling** → Engine rule: "Level up" (CRITICAL priority)
3. **Equipment Slots** → Engine rule: "Equipment slot pending" (CRITICAL priority)
4. **Item On Ground** → Engine rule: "Item pickup menu" (HIGH priority)
5. **Enemy Detection** → Engine rule: "Combat (autofight)" (NORMAL priority)
6. **Health Recovery** → Engine rule: "Rest to recover" (NORMAL priority)
7. **Exploration** → Engine rule: "Explore (good health)" (NORMAL priority)
8. **Menu Navigation** → Various CRITICAL rules for prompts

## Test Requirements

### Unit Tests
- Continue running: `pytest tests/ -q`
- Expected: 216+ tests passing
- Regression tolerance: 0

### Integration Tests (New)
- **Test File**: `tests/test_engine_vs_legacy.py` (to be created)
- **Approach**: Run same scenarios with both implementations
- **Validation**: Decisions should be identical or equivalent

### Real Game Tests
- **Command**: `timeout 600 python main.py --steps 50 --use-engine --debug`
- **Timeout**: 10 seconds per step = 500 seconds for 50 steps
- **Validation**: Game completes without errors, sensible decisions

## Metrics to Track

| Metric | Baseline | Target | Success |
|--------|----------|--------|---------|
| Legacy lines | 769 | <400 | Reduce 50%+ |
| Engine rules | 24 | 25-30 | Add 1-6 if needed |
| Test coverage | 216 | 240+ | Add 24+ tests |
| Pass rate | 100% | 100% | Maintain |
| Decision latency | TBD | <10ms | Performance OK |
| Game run length | 50 moves | 200+ | Stability |

## Expected Outcomes

### By End of Week 4
✅ DecisionEngine fully handling all decision logic
✅ `_decide_action_legacy()` reduced from 769 to ~350-400 lines OR removed entirely
✅ `use_decision_engine` flag can be set to True by default
✅ 240+ tests passing (216 existing + 24 new for engine comparisons)
✅ Real game validates with 200+ move runs
✅ Zero regressions from original implementation

## Potential Issues & Mitigations

### Issue: Engine missing a decision scenario
**Mitigation**: Add new rule, test, then migrate

### Issue: Engine decisions differ from legacy
**Mitigation**: This is expected - engine should be smarter. Validate new decisions are correct.

### Issue: Performance degradation
**Mitigation**: Profile rule evaluation, cache conditions if needed

### Issue: Real game fails with engine
**Mitigation**: Enable detailed logging, compare decisions step-by-step with legacy

## Next Immediate Steps

1. Analyze `_decide_action_legacy()` (lines 1626-2395) for rule mapping
2. Create `test_engine_vs_legacy.py` for comparison testing
3. Run baseline tests: `pytest tests/ -q` (expected: 216 passing)
4. Run baseline game: 50 moves without engine (expected: success)
5. Run with engine: 50 moves with `--use-engine` (expected: success, same or better decisions)

## Files to Modify

1. **decision_engine.py**: Add any missing rules
2. **bot.py**: Update `_decide_action_legacy()` to remove dead code
3. **tests/test_engine_vs_legacy.py**: NEW - comparison tests
4. **tests/**: Any new rule-specific tests
5. **Documentation**: Update README, ARCHITECTURE.md, DEVELOPER_GUIDE.md

## Success Criteria (Week 3-4)

✅ Complete audit of legacy code done
✅ All required rules added to engine
✅ 216+ tests passing
✅ Real game test 50+ moves with engine succeeds
✅ Code size reduced by 50%+ OR deemed acceptable smaller reduction
✅ Zero regressions detected
✅ Documentation updated
✅ Ready to merge to production with `use_decision_engine=True` by default

---

**Ready to proceed with Phase 3b Week 3-4 migration!**
