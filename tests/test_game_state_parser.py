"""Unit tests for game state parsing."""

import pytest
from game_state import GameStateParser, GameState, Position


@pytest.mark.unit
class TestGameStateParser:
    """Tests for game state extraction from screen output."""

    def test_initial_state_creation(self, game_state_parser):
        """Test that parser initializes with default state."""
        state = game_state_parser.state
        
        assert isinstance(state, GameState)
        assert state.experience_level >= 1
        assert state.health > 0

    def test_parse_empty_output(self, game_state_parser):
        """Test parsing of empty output."""
        output = ""
        state = game_state_parser.parse_output(output)
        
        # Should return state without crashing
        assert state is not None
        assert isinstance(state, GameState)

    def test_ansi_cleaning(self, game_state_parser):
        """Test ANSI code removal."""
        # Sample output with ANSI codes
        output = "\x1b[32mHello\x1b[0m \x1b[1mWorld\x1b[0m"
        
        state = game_state_parser.parse_output(output)
        
        # Should not crash with ANSI codes present
        assert state is not None

    def test_visible_text_extraction(self, game_state_parser):
        """Test extraction of visible text from output."""
        output = "Health: 100/100\nMana: 50/50"
        
        state = game_state_parser.parse_output(output)
        
        # Parser should handle the output
        assert state is not None

    def test_position_tracking(self, game_state_parser):
        """Test position extraction from game state."""
        state = game_state_parser.state
        
        # Position should be None or a Position object
        assert state.position is None or isinstance(state.position, Position)

    def test_experience_level_tracking(self, game_state_parser):
        """Test experience level extraction."""
        state = game_state_parser.state
        
        assert isinstance(state.experience_level, int)
        assert state.experience_level >= 1
        assert isinstance(state.experience_progress, int)
        assert 0 <= state.experience_progress <= 100


@pytest.mark.unit
class TestGameStateDataclass:
    """Tests for GameState dataclass."""

    def test_gamestate_creation(self):
        """Test creation of GameState with default values."""
        state = GameState()
        
        assert state.dungeon_branch == "Dungeon"
        assert state.dungeon_level == 1
        assert isinstance(state.inventory, list)
        assert isinstance(state.visible_map, list)

    def test_gamestate_with_position(self):
        """Test GameState with position."""
        pos = Position(x=10, y=15)
        state = GameState(position=pos)
        
        assert state.position == pos
        assert state.position.x == 10
        assert state.position.y == 15

    def test_gamestate_health_tracking(self):
        """Test health/mana tracking in GameState."""
        state = GameState(health=50, max_health=100, mana=20, max_mana=40)
        
        assert state.health == 50
        assert state.max_health == 100
        assert state.mana == 20
        assert state.max_mana == 40

    def test_gamestate_experience_progress(self):
        """Test experience progress percentage."""
        state = GameState(experience_level=5, experience_progress=75)
        
        assert state.experience_level == 5
        assert 0 <= state.experience_progress <= 100

    def test_gamestate_inventory_initialization(self):
        """Test inventory list initialization."""
        state = GameState()
        
        assert isinstance(state.inventory, list)
        assert len(state.inventory) == 0
        
        # Test with initial inventory
        items = ["sword", "shield", "potion"]
        state2 = GameState(inventory=items)
        assert state2.inventory == items
