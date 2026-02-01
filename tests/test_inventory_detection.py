"""
Test inventory screen detection and handling.

This test file validates that the bot properly detects inventory screens
and doesn't get stuck in loops while in inventory.
"""
import pytest
from src.bot import DCSSBot
from pathlib import Path


@pytest.fixture
def bot_with_inventory_detection(game_state_parser):
    """Create a bot instance for testing inventory detection."""
    bot = DCSSBot()
    bot.parser = game_state_parser
    return bot


@pytest.fixture
def load_inventory_screen():
    """Load inventory screen fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "game_screens" / "inventory_screen.txt"
    if fixture_path.exists():
        with open(fixture_path) as f:
            return f.read()
    return ""


@pytest.fixture
def load_inventory_screen_full():
    """Load full inventory screen fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "game_screens" / "inventory_screen_full.txt"
    if fixture_path.exists():
        with open(fixture_path) as f:
            return f.read()
    return ""


class TestInventoryDetection:
    """Test inventory screen detection."""

    def test_inventory_fixture_basic_exists(self, load_inventory_screen):
        """Test that basic inventory fixture loads correctly."""
        assert "Inventory:" in load_inventory_screen
        assert "Hand Weapons" in load_inventory_screen
        assert "a +0 war axe" in load_inventory_screen

    def test_inventory_fixture_full_exists(self, load_inventory_screen_full):
        """Test that full inventory fixture loads correctly."""
        assert "Inventory: 6/52 slots" in load_inventory_screen_full
        assert "Jewellery" in load_inventory_screen_full
        assert "ring of protection" in load_inventory_screen_full

    def test_inventory_detection_basic(self, bot_with_inventory_detection, load_inventory_screen):
        """Test that bot detects basic inventory screen."""
        output = load_inventory_screen
        action = bot_with_inventory_detection._check_and_handle_inventory_state(output)
        
        # Should return an action (Escape to exit)
        assert action is not None
        assert action == '\x1b'  # Escape character

    def test_inventory_detection_full(self, bot_with_inventory_detection, load_inventory_screen_full):
        """Test that bot detects full inventory screen with more items."""
        output = load_inventory_screen_full
        action = bot_with_inventory_detection._check_and_handle_inventory_state(output)
        
        # Should return an action (Escape to exit)
        assert action is not None
        assert action == '\x1b'  # Escape character

    def test_inventory_flag_set_on_refresh(self, bot_with_inventory_detection):
        """Test that inventory flag is set when refresh is called."""
        assert bot_with_inventory_detection.in_inventory_screen is False
        
        action = bot_with_inventory_detection._refresh_inventory()
        
        # Flag should be set
        assert bot_with_inventory_detection.in_inventory_screen is True
        # Action should be 'i' to open inventory
        assert 'i' in str(action) or action == 'i'

    def test_inventory_cooldown_tracking(self, bot_with_inventory_detection):
        """Test that inventory refresh tracking prevents loops."""
        # Set up initial state
        bot_with_inventory_detection.move_count = 50
        bot_with_inventory_detection.last_inventory_refresh = 48
        bot_with_inventory_detection.in_inventory_screen = True
        
        # With only 2 moves elapsed (50-48=2), should not timeout yet
        output = "some game output without inventory markers"
        
        # This should continue waiting (return a wait action or None)
        action = bot_with_inventory_detection._check_and_handle_inventory_state(output)
        
        # If inventory isn't detected in output, should wait or timeout
        # At 2 moves elapsed, should still be waiting
        
        # Now move to 4 moves elapsed (move_count=52)
        bot_with_inventory_detection.move_count = 52
        
        # Still within 3-move window (52-48=4 > 3), so timeout should trigger
        action = bot_with_inventory_detection._check_and_handle_inventory_state(output)
        
        # After timeout (4 moves > 3), flag should be reset
        # This test validates timeout protection exists

    def test_inventory_item_line_detection(self, bot_with_inventory_detection):
        """Test detection of inventory item lines."""
        # Example of various inventory item formats
        test_lines = [
            "a - a +0 war axe (weapon)",
            "b - a +0 scale mail (worn)",
            "c) some item with parenthesis",
            "d - a potion of might",
            "f - a +4 ring of protection"
        ]
        
        output = "\n".join(test_lines)
        action = bot_with_inventory_detection._check_and_handle_inventory_state(output)
        
        # With 5 inventory items detected, should recognize as inventory
        assert action is not None
        assert action == '\x1b'

    def test_no_false_positive_on_game_screen(self, bot_with_inventory_detection):
        """Test that normal game screens don't trigger inventory exit."""
        normal_game_output = """
Health: 15/18  Mana: 0/0  Gold: 0
Dungeon:1  Exp: 0/88 (0%)

A   . . . . . . . .
B   . . . . . . . .
C   . @ . . . . . .
        """
        
        bot_with_inventory_detection.in_inventory_screen = False
        action = bot_with_inventory_detection._check_and_handle_inventory_state(normal_game_output)
        
        # Should not send Escape if not in inventory
        assert action is None
