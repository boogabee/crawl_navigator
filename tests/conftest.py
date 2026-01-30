"""Conftest for pytest fixtures and configuration."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def crawl_command():
    """Provide the Crawl command for testing."""
    return "/usr/games/crawl"


@pytest.fixture
def char_creation_state_machine():
    """Provide a fresh CharacterCreationStateMachine instance."""
    from char_creation_state_machine import CharacterCreationStateMachine
    return CharacterCreationStateMachine()


@pytest.fixture
def game_state_tracker():
    """Provide a fresh GameStateMachine instance."""
    from game_state_machine import GameStateMachine
    return GameStateMachine()


@pytest.fixture
def game_state_parser():
    """Provide a fresh GameStateParser instance."""
    from game_state import GameStateParser
    return GameStateParser()

@pytest.fixture
def game_screens():
    """Load actual game screen files for testing against real game output."""
    screens_dir = Path(__file__).parent / "fixtures" / "game_screens"
    screens = {}
    
    if screens_dir.exists():
        for screen_file in sorted(screens_dir.glob("*.txt")):
            with open(screen_file, 'r') as f:
                screens[screen_file.stem] = f.read()
    
    return screens


@pytest.fixture
def game_screen_startup_early_game(game_screens):
    """Early game startup screen with minimal info."""
    return game_screens.get("startup_early_game", "")


@pytest.fixture
def game_screen_single_enemy(game_screens):
    """Screen with a single enemy (hobgoblin)."""
    return game_screens.get("single_enemy_hobgoblin", "")


@pytest.fixture
def game_screen_multiple_enemies(game_screens):
    """Screen with multiple enemies (endoplasm and kobold)."""
    return game_screens.get("multiple_enemies", "")


@pytest.fixture
def game_screen_different_run(game_screens):
    """Screen from a different game run with enemy (quokka)."""
    return game_screens.get("different_run_enemy", "")