# Game Screen Test Fixtures

This directory contains actual DCSS game screen output used for testing bot functionality against real game behavior.

## Available Fixtures

### startup_early_game.txt
- **Source**: screens_20260129_184821/0011_visual.txt
- **Move**: #6
- **Description**: Early game startup with a newly discovered quokka
- **Game State**: Single enemy (quokka), Health: 17/18, Level 1
- **Use Case**: Testing basic game state parsing and startup detection

### single_enemy_hobgoblin.txt
- **Source**: screens_20260129_184821/0037_visual.txt
- **Move**: #32
- **Description**: Screen with one enemy visible (hobgoblin)
- **Game State**: Single enemy (hobgoblin), Health: 24/24, Level 2
- **Use Case**: Testing single enemy detection and extraction from TUI monsters list

### multiple_enemies.txt
- **Source**: screens_20260129_184821/0090_visual.txt
- **Move**: #85
- **Description**: Screen with multiple enemies visible simultaneously
- **Game State**: Two enemies (endoplasm + kobold), Health: 20/24, Level 2
- **Use Case**: Testing multiple enemy handling and prioritization

### different_run_enemy.txt
- **Source**: screens_20260130_053610/0011_visual.txt
- **Move**: #6
- **Description**: Early game screen from a different run with quokka
- **Game State**: Single enemy (quokka), Health: 17/18, Level 1
- **Use Case**: Regression testing - ensures parsing works consistently across runs

## Usage in Tests

These fixtures are loaded via pytest fixtures in `conftest.py`:

```python
@pytest.fixture
def game_screen_single_enemy(game_screens):
    """Screen with a single enemy (hobgoblin)."""
    return game_screens.get("single_enemy_hobgoblin", "")
```

All fixtures are automatically loaded and available as pytest fixtures:
- `game_screens`: Dictionary of all available screens
- `game_screen_startup_early_game`: Early game screen
- `game_screen_single_enemy`: Single enemy screen
- `game_screen_multiple_enemies`: Multiple enemies screen
- `game_screen_different_run`: Different run screen

## Test Coverage

Tests in `tests/test_real_game_screens.py` use these fixtures to validate:
- Enemy extraction from TUI monsters section
- Single vs. multiple enemy handling
- Enemy name identification
- Game state parsing (health, level, etc.)
- Consistency across different game runs
- False positive prevention in enemy detection

## Adding New Fixtures

To add new game screen fixtures:

1. Copy a visual screen file from `logs/screens_*/0*_visual.txt`
2. Place it in this directory with a descriptive name
3. Add a corresponding fixture to `conftest.py`
4. Add test cases in `tests/test_real_game_screens.py`
5. Document the fixture in this README

