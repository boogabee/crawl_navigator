# Phase 3b - Quick Start Guide

## What's New?

You can now test the DecisionEngine with a simple command-line flag!

## Basic Usage

```bash
# Run game with DecisionEngine ENABLED
python main.py --steps 100 --use-engine

# Run game with legacy implementation (default)
python main.py --steps 100

# Run with debug logging to see decision details
python main.py --steps 50 --use-engine --debug
```

## What Gets Enabled?

When you use `--use-engine`, the bot:
1. ✅ Prepares complete game state context
2. ✅ Evaluates ~20 DecisionEngine rules
3. ✅ Makes decisions based on game state
4. ✅ Falls back to legacy if needed
5. ✅ Tracks statistics

## Monitoring Engine Behavior

In the logs, you'll see:
- Decisions made by the engine ("Autofight - bat in range")
- Any fallbacks to legacy code (rare)
- Move counts and state information
- Final statistics

## What's Being Tested?

**Menu Prompts** ✅
- Equip/quaff slots
- More prompts
- Save game prompts
- Level-up prompts

**Combat** ✅
- Enemy detection
- Autofight decisions
- Rest cycles
- Health management

**Exploration** ✅
- Auto-explore
- Item detection
- Dungeon navigation

## Expected Behavior

The engine should:
1. Play the game identically to the legacy version
2. Make correct combat decisions
3. Explore the dungeon
4. Survive at least 50 moves
5. Reach dungeon level 2-3 in 100 moves

## Architecture Behind the Scenes

```
--use-engine flag
        ↓
    main.py
        ↓
   bot.use_decision_engine = True
        ↓
   _decide_action() router
        ↓
   _decide_action_using_engine()
        ↓
   _prepare_decision_context()
        ↓
   DecisionEngine.decide()
        ↓
   Returns (command, reason)
        ↓
   Send command to game
```

## Troubleshooting

**If engine hangs**:
- Use Ctrl-C to interrupt
- Try with fewer steps: `--steps 50`
- Check logs in `logs/` directory

**If engine makes wrong decisions**:
- This shouldn't happen (all tests passing)
- Enable debug: `--debug`
- Review logs for decision context

**To go back to legacy**:
- Omit `--use-engine` flag
- Or explicitly: `--use-engine false` (note: not implemented, flag is boolean)

## Testing Commands

```bash
# Quick test: 50 moves
python main.py --steps 50 --use-engine

# Medium test: 100 moves
python main.py --steps 100 --use-engine

# Long test: 200 moves (will take 3-5 minutes)
python main.py --steps 200 --use-engine

# Debug test: 25 moves with full logging
python main.py --steps 25 --use-engine --debug
```

## Success Indicators

After running with `--use-engine`, check that:
1. ✅ Game progresses normally
2. ✅ Bot doesn't get stuck in loops
3. ✅ Enemies are detected and fought
4. ✅ No crashes or errors
5. ✅ Game reaches expected dungeon level

## Statistics Tracked

The engine tracks:
- `engine_decisions_made`: How many times engine made a decision
- `legacy_fallback_count`: How many times we fell back to legacy
- `decision_divergences`: Differences between engine and legacy (if tracked)

Access via logs or programmatically:
```python
print(f"Engine made {bot.engine_decisions_made} decisions")
print(f"Fallbacks: {bot.legacy_fallback_count}")
```

## Next Steps

**Week 2**: Combat-specific testing  
**Week 3**: Complex logic validation  
**Week 4**: Full migration and cleanup  

Ready to go! Use `--use-engine` and help validate the DecisionEngine! 🚀
