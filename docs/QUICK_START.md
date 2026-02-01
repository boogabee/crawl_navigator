# Quick Start Guide

## Installation

### Prerequisites
- Python 3.10+
- Dungeon Crawl Stone Soup installed locally
- Linux system

### Setup Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify Crawl installation**:
   ```bash
   which crawl
   # or
   /usr/games/crawl --version
   ```

3. **Configure bot** (optional):
   Edit `src/utils/credentials.py` to change Crawl command if needed.

## Running the Bot

### Basic Usage
```bash
python main.py
```

### Run for Limited Steps
```bash
python main.py --steps 100
```

### Debug Mode
```bash
python main.py --debug
```

### Combine Options
```bash
python main.py --steps 50 --debug
```

### Run Tests
```bash
bash scripts/run_tests.sh
```
Or with pytest directly:
```bash
pytest tests/ -v
```

## Screenshot Logs

The bot automatically saves screenshots of each screen to `logs/screens_TIMESTAMP/` directory:

**Character Creation Phase**:
- Screen 0001: Initial startup menu
- Screen 0002: Race selection menu
- Screen 0003: Class selection menu
- Screen 0004: Background selection menu
- Screen 0005: Skills/equipment selection menu
- Screen 0006+: Gameplay screens (each move)

Each screen is saved in three formats:
- `*_raw.txt`: Raw game output with ANSI codes
- `*_clean.txt`: Game output with ANSI codes removed (readable text)
- `*_visual.txt`: Full accumulated screen state with visible borders

An `index.txt` file tracks all captures with move numbers and action context.

## What to Expect

The bot displays a **unified interface** with two sections:

### Top Section: Game TUI
- Full Dungeon Crawl display
- Character stats (HP, Mana, Level, Depth)
- Dungeon map and game messages

### Bottom Section: Activity Panel
- 12 lines showing bot actions and events
- Timestamped messages: `[HH:MM:SS]`
- Color-coded by type:
  - ✓ Green = Success events
  - ℹ Default = Normal actions
  - ⚠ Yellow = Warnings
  - ✗ Red = Errors
  - ⚙ Cyan = Debug info

### Startup Flow
1. **PTY Setup**: Creates local Crawl connection in cbreak mode (character-by-character with echo)
2. **Name Entry**: Sends character name one character at a time, then Enter (logged to activity panel)
3. **Game Auto-advance**: Game automatically selects "Dungeon Crawl" and proceeds to character menus
4. **Character Creation**: Bot navigates species/class/background menus automatically (logged)
5. **Gameplay**: Game starts, unified display activates
6. **Bot Loop**: Moves and actions logged to activity panel
7. **Exit**: Graceful shutdown after steps or Ctrl+C

**Terminal Emulation**: The bot uses **cbreak mode** (not raw mode) for the PTY:
- Sends individual keypresses to the game
- Receives echoed input + game output for proper feedback
- Allows signal handling and proper menu navigation

## Troubleshooting

### "Command 'crawl' not found"
```bash
# Install Crawl
sudo apt install crawl

# Or use full path in credentials.py
CRAWL_COMMAND = '/usr/games/crawl'
```

### "No startup menu received"
- Ensure Crawl is installed: `crawl --version`
- Check terminal is 100+ characters wide
- Try running `crawl` manually first

### Bot stuck at menu
- Press Ctrl+C to exit
- Check if character save is corrupted: `ls ~/.crawl/saves/`
- Try creating new character

## File Structure

```
├── main.py                    # Entry point
├── bot.py                     # Main bot logic
├── local_client.py            # PTY management
├── game_state.py              # State parsing
├── game_state_machine.py      # State tracking
├── char_creation_state_machine.py  # Character automation
├── credentials.py             # Configuration
└── requirements.txt           # Dependencies
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for implementation
- Review [CHANGELOG.md](CHANGELOG.md) for known issues
