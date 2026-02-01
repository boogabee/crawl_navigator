"""Tests for blessed-based display utilities."""

import pytest
from examples.bot_display import BotDisplay, DebugDisplay, ScreenBuffer


@pytest.mark.unit
class TestBotDisplay:
    """Tests for BotDisplay class."""
    
    @pytest.fixture
    def display(self):
        """Create display instance."""
        return BotDisplay(width=160, height=40)
    
    def test_initialization(self, display):
        """Test display initialization."""
        assert display.width == 160
        assert display.height == 40
        assert display.term is not None
    
    def test_header_formatting(self, display):
        """Test header formatting."""
        result = display.header("Test Header")
        assert "Test Header" in result
        assert "=" in result
    
    def test_success_message(self, display):
        """Test success message formatting."""
        result = display.success("Operation completed")
        assert "Operation completed" in result
        assert "✓" in result
    
    def test_error_message(self, display):
        """Test error message formatting."""
        result = display.error("Something went wrong")
        assert "Something went wrong" in result
        assert "✗" in result
    
    def test_warning_message(self, display):
        """Test warning message formatting."""
        result = display.warning("Be careful")
        assert "Be careful" in result
        assert "⚠" in result
    
    def test_info_message(self, display):
        """Test info message formatting."""
        result = display.info("Information")
        assert "Information" in result
        assert "ℹ" in result
    
    def test_status_line(self, display):
        """Test status line formatting."""
        result = display.status("Health", "50/100", "green")
        assert "Health" in result
        assert "50/100" in result
    
    def test_game_state_display(self, display):
        """Test game state display."""
        state_info = {
            "state": "GAMEPLAY",
            "health": 50,
            "max_health": 100,
            "mana": 20,
            "max_mana": 40,
            "exp_level": 3,
            "exp_progress": 45,
            "gold": 150,
        }
        result = display.game_state_display(state_info)
        assert "GAME STATE" in result
        assert "GAMEPLAY" in result
        assert "50/100" in result
    
    def test_action_display(self, display):
        """Test action display."""
        result = display.action_display("Move", "Right")
        assert "Move" in result
        assert "Right" in result
        assert "→" in result
    
    def test_move_count(self, display):
        """Test move counter display."""
        result = display.move_count(42, 3.5)
        assert "42" in result
        assert "3.5" in result
    
    def test_separator(self, display):
        """Test separator line."""
        result = display.separator()
        assert "-" in result
        assert len(result) > 10
    
    def test_section_formatting(self, display):
        """Test section formatting."""
        result = display.section("Test Section", "Content here")
        assert "Test Section" in result
        assert "Content here" in result


@pytest.mark.unit
class TestDebugDisplay:
    """Tests for DebugDisplay class."""
    
    @pytest.fixture
    def display(self):
        """Create debug display instance."""
        return DebugDisplay(width=160, height=40)
    
    def test_state_machine_debug(self, display):
        """Test state machine debug display."""
        history = ["start", "race", "class", "background"]
        result = display.state_machine_debug("background", False, history)
        assert "STATE MACHINE DEBUG" in result
        assert "background" in result
        assert "OK" in result or "✓" in result
    
    def test_state_machine_debug_stuck(self, display):
        """Test state machine debug with stuck indication."""
        history = ["start", "race", "race", "race"]
        result = display.state_machine_debug("race", True, history)
        assert "STUCK" in result
    
    def test_performance_stats(self, display):
        """Test performance stats display."""
        result = display.performance_stats(100, 45.5, 2.2)
        assert "100" in result  # moves
        assert "45.5" in result  # elapsed
        assert "2.2" in result  # speed
    
    def test_screen_capture_info(self, display):
        """Test screen capture info."""
        result = display.screen_capture_info(160, 40, 35)
        assert "160" in result
        assert "40" in result
        assert "35" in result


@pytest.mark.unit
class TestScreenBuffer:
    """Tests for ScreenBuffer class."""
    
    @pytest.fixture
    def buffer(self):
        """Create screen buffer instance."""
        return ScreenBuffer(width=160, height=40)
    
    def test_initialization(self, buffer):
        """Test buffer initialization."""
        assert buffer.width == 160
        assert buffer.height == 40
        assert buffer.display is not None
    
    def test_display_instance(self, buffer):
        """Test that buffer has display instance."""
        assert isinstance(buffer.display, BotDisplay)


@pytest.mark.unit
class TestDisplayIntegration:
    """Integration tests for display components."""
    
    def test_complete_game_display_flow(self):
        """Test complete display flow."""
        display = BotDisplay()
        
        # Create mock state
        state_info = {
            "state": "GAMEPLAY",
            "health": 75,
            "max_health": 100,
            "mana": 30,
            "max_mana": 50,
            "exp_level": 5,
            "exp_progress": 60,
            "gold": 250,
            "hunger": "satisfied",
            "location": "D:3",
        }
        
        # Test display generation doesn't crash
        output = display.game_state_display(state_info)
        assert output is not None
        assert "GAMEPLAY" in output
    
    def test_action_sequence_display(self):
        """Test displaying action sequence."""
        display = BotDisplay()
        
        actions = [
            ("Move", "North"),
            ("Rest", ""),
            ("Attack", "Goblin"),
        ]
        
        output = []
        for action, detail in actions:
            output.append(display.action_display(action, detail))
        
        assert len(output) == 3
        assert all("→" in line for line in output)
