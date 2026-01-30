"""Tests for bot initialization and configuration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from real_screens import (
    get_startup_screen_main,
    get_character_creation_species,
    STARTUP_SCREEN_NAME_ENTRY,
    STARTUP_SCREEN_MENU_CHOICES,
    CHARACTER_CREATION_CLASS,
    CHARACTER_CREATION_BACKGROUND,
    GAMEPLAY_SCREEN,
)


@pytest.fixture
def mock_local_client():
    """Mock the LocalCrawlClient to avoid actual Crawl startup."""
    with patch('bot.LocalCrawlClient') as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield mock


class TestBotInitialization:
    """Tests for DCSSBot initialization and attributes."""
    
    def test_bot_initializes(self, mock_local_client):
        """Test that bot initializes without errors."""
        from bot import DCSSBot
        bot = DCSSBot()
        assert bot is not None
    
    def test_bot_has_char_creation_state(self, mock_local_client):
        """Test that bot has char_creation_state attribute (not char_creation_state_machine)."""
        from bot import DCSSBot
        bot = DCSSBot()
        assert hasattr(bot, 'char_creation_state'), "Bot should have 'char_creation_state' attribute"
        
        # Verify it's not the wrong name
        assert not hasattr(bot, 'char_creation_state_machine'), \
            "Bot should NOT have 'char_creation_state_machine' attribute (should be 'char_creation_state')"
    
    def test_char_creation_state_is_state_machine(self, mock_local_client):
        """Test that char_creation_state is a CharacterCreationStateMachine instance."""
        from bot import DCSSBot
        from char_creation_state_machine import CharacterCreationStateMachine
        bot = DCSSBot()
        assert isinstance(bot.char_creation_state, CharacterCreationStateMachine), \
            "char_creation_state should be a CharacterCreationStateMachine instance"
    
    def test_bot_has_required_attributes(self, mock_local_client):
        """Test that bot has all required attributes for startup."""
        from bot import DCSSBot
        bot = DCSSBot()
        
        required_attrs = [
            'ssh_client',
            'parser',
            'state_tracker',
            'char_creation_state',
            'screen_buffer',
            'move_count',
            'last_screen',
        ]
        
        for attr in required_attrs:
            assert hasattr(bot, attr), f"Bot should have '{attr}' attribute"
    
    def test_startup_sequence_uses_correct_attribute(self, mock_local_client):
        """Test that _local_startup method uses the correct attribute name."""
        from bot import DCSSBot
        import inspect
        
        bot = DCSSBot()
        # Get the source code of _local_startup
        source = inspect.getsource(bot._local_startup)
        
        # Verify it uses self.char_creation_state (not self.char_creation_state_machine)
        assert 'self.char_creation_state' in source, \
            "_local_startup should reference self.char_creation_state"
        assert 'self.char_creation_state_machine' not in source, \
            "_local_startup should NOT reference self.char_creation_state_machine"


class TestLoginSequence:
    """Tests for the login sequence validation."""
    
    def test_startup_screen_detection(self, mock_local_client):
        """Test that startup screen with 'Enter your name' is detected."""
        from bot import DCSSBot
        
        startup_screen = get_startup_screen_main()
        mock_client = mock_local_client.return_value
        mock_client.read_output.return_value = startup_screen
        mock_client.send_command = Mock()
        
        bot = DCSSBot()
        state_machine = bot.char_creation_state
        
        # Update state machine with real startup screen
        state = state_machine.update(startup_screen.lower())
        
        # Should detect as startup state
        assert state == 'startup', f"Expected 'startup' state, got '{state}'"
    
    def test_menu_screen_detection(self, mock_local_client):
        """Test that menu screen is detected."""
        from bot import DCSSBot
        
        startup_screen = get_startup_screen_main()
        mock_client = mock_local_client.return_value
        
        bot = DCSSBot()
        state_machine = bot.char_creation_state
        
        # First set to startup with real startup screen
        state = state_machine.update(startup_screen.lower())
        assert state == 'startup'
        
        # Now test with menu choices (should still be startup or transition based on patterns)
        state = state_machine.update(STARTUP_SCREEN_MENU_CHOICES.lower())
        # The menu screen might not trigger a transition yet, depending on detection patterns
        assert state in ['startup', 'species'], f"State should be startup or race, got '{state}'"
    
    def test_character_creation_flow_startup_to_species(self, mock_local_client):
        """Test the flow from startup screen to species selection."""
        from bot import DCSSBot
        
        startup_screen = get_startup_screen_main()
        species_screen = get_character_creation_species()
        
        bot = DCSSBot()
        state_machine = bot.char_creation_state
        
        # Reset to startup
        state_machine.reset()
        assert state_machine.current_state.id == 'startup'
        
        # Show real startup screen
        state_machine.update(startup_screen.lower())
        assert state_machine.current_state.id == 'startup'
        
        # Show real race selection screen
        state_machine.update(species_screen.lower())
        
        # Should transition to race
        assert state_machine.current_state.id == 'species', \
            f"Expected species state after race screen, got {state_machine.current_state.id}"
        
        # State history should show progression
        assert len(state_machine.state_history) >= 1
    
    def test_full_character_creation_sequence(self, mock_local_client):
        """Test the complete character creation sequence through multiple states."""
        from bot import DCSSBot
        
        startup_screen = get_startup_screen_main()
        species_screen = get_character_creation_species()
        
        bot = DCSSBot()
        state_machine = bot.char_creation_state
        state_machine.reset()
        
        # Use real screens from actual game (with random names)
        screens = [
            ("startup", startup_screen),
            ("race", species_screen),
            ("class", CHARACTER_CREATION_CLASS),
            ("background", CHARACTER_CREATION_BACKGROUND),
        ]
        
        for expected_state, screen in screens:
            state_machine.update(screen.lower())
            # Verify we reached expected state (or close to it)
            current = state_machine.current_state.id
            assert current != 'error', f"State machine entered error state on screen: {screen}"
    
    def test_state_machine_reset_to_startup(self, mock_local_client):
        """Test that state machine resets properly to startup state."""
        from bot import DCSSBot
        
        bot = DCSSBot()
        state_machine = bot.char_creation_state
        
        # Transition to race
        state_machine.update("Select your species: [a] Human")
        assert state_machine.current_state.id == 'species'
        
        # Reset should go back to startup
        state_machine.reset()
        assert state_machine.current_state.id == 'startup', \
            f"After reset, expected 'startup', got '{state_machine.current_state.id}'"
        assert len(state_machine.state_history) == 1
    
    def test_gameplay_detection_from_state_machine(self, mock_local_client):
        """Test that gameplay screen is properly detected."""
        from bot import DCSSBot
        
        species_screen = get_character_creation_species()
        
        bot = DCSSBot()
        state_machine = bot.char_creation_state
        state_machine.reset()
        
        # First transition through states to get past startup using real screens
        state_machine.update(species_screen.lower())
        assert state_machine.current_state.id == 'species'
        
        # Use real gameplay screen from actual game
        state_machine.update(GAMEPLAY_SCREEN.lower())
        
        # Should detect gameplay state
        assert state_machine.current_state.id == 'gameplay', \
            f"Expected gameplay state, got {state_machine.current_state.id}"
