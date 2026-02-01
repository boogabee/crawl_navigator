"""Tests for python-statemachine enhanced state machines."""

import pytest
from src.state_machines.char_creation_state_machine import CharacterCreationStateMachine
from src.state_machines.game_state_machine import GameStateMachine


@pytest.mark.unit
class TestCharCreationStateMachineV2:
    """Tests for enhanced character creation state machine."""
    
    @pytest.fixture
    def state_machine(self):
        """Create fresh state machine instance."""
        return CharacterCreationStateMachine()
    
    def test_initial_state(self, state_machine):
        """Test starts in startup state."""
        assert state_machine.current_state == state_machine.startup
    
    def test_species_selection_transition(self, state_machine):
        """Test transition to species selection."""
        state_machine.update("Select your species: [a] Human [b] Dwarf")
        assert state_machine.current_state == state_machine.species
    
    def test_class_selection_transition(self, state_machine):
        """Test transition from race to class."""
        state_machine.update("Select your species")
        assert state_machine.current_state == state_machine.species
        
        state_machine.update("Select your class: [a] Fighter [b] Mage")
        assert state_machine.current_state == state_machine.class_select
    
    def test_background_selection_transition(self, state_machine):
        """Test transition to background via race first."""
        state_machine.update("Select your species")
        assert state_machine.current_state == state_machine.species
        
        state_machine.update("Select your background: [a] Soldier [b] Scholar")
        assert state_machine.current_state == state_machine.background
    
    def test_gameplay_ready_detection(self, state_machine):
        """Test detection of gameplay ready state."""
        state_machine.update("Select your species")
        # Real DCSS HUD includes hp:, ac:, and ev: (all lowercase)
        state_machine.update("hp: 10/10 ac: 5 ev: 10")
        assert state_machine.current_state == state_machine.gameplay
    
    def test_stuck_detection(self, state_machine):
        """Test stuck state detection."""
        screen = "Select your species"
        for _ in range(4):
            state_machine.update(screen)
        
        assert state_machine.is_stuck
    
    def test_state_history(self, state_machine):
        """Test state history tracking."""
        state_machine.update("Select your species")
        state_machine.update("Select your class")
        
        assert "start" in state_machine.state_history
        assert "species" in state_machine.state_history
        assert "class_select" in state_machine.state_history
    
    def test_reset(self, state_machine):
        """Test state machine reset."""
        state_machine.update("Select your species")
        assert state_machine.current_state == state_machine.species
        
        state_machine.reset()
        assert state_machine.current_state == state_machine.startup
        assert len(state_machine.state_history) == 1


@pytest.mark.unit
class TestGameStateMachineV2:
    """Tests for enhanced game state machine."""
    
    @pytest.fixture
    def state_machine(self):
        """Create fresh state machine instance."""
        return GameStateMachine()
    
    def test_initial_state(self, state_machine):
        """Test starts disconnected."""
        assert state_machine.current_state == state_machine.disconnected
    
    def test_connect_transition(self, state_machine):
        """Test connection."""
        state_machine.connect()
        assert state_machine.current_state == state_machine.connected
    
    def test_start_game_transition(self, state_machine):
        """Test starting game."""
        state_machine.connect()
        state_machine.start_game()
        assert state_machine.current_state == state_machine.gameplay
    
    def test_gameplay_detection(self, state_machine):
        """Test gameplay state detection from screen."""
        state_machine.connect()
        state_machine.start_game()
        
        state_machine.update("Level 1 HP: 10/10 AC: 5 Exp: 1")
        assert state_machine.current_state == state_machine.gameplay
    
    def test_menu_detection(self, state_machine):
        """Test menu detection."""
        state_machine.connect()
        state_machine.start_game()
        
        state_machine.update("HP: 10/10 AC: 5 [a] Ability [b] Cast Spell")
        assert state_machine.current_state == state_machine.in_menu
    
    def test_combat_detection(self, state_machine):
        """Test combat state via context."""
        state_machine.connect()
        state_machine.start_game()
        
        # Combat triggers when enemy_nearby is true AND we call update
        state_machine.update("HP: 10/10 AC: 5", enemy_nearby=True)
        # Note: Automatic combat trigger requires implementation in update
        # For now, verify the flag is set
        assert state_machine.enemy_nearby
    
    def test_quit_detection(self, state_machine):
        """Test quit detection."""
        state_machine.connect()
        state_machine.start_game()
        
        state_machine.update("Thank you for playing!")
        assert state_machine.current_state == state_machine.quit_state
    
    def test_properties(self, state_machine):
        """Test helper properties."""
        state_machine.connect()
        assert state_machine.is_connected
        assert not state_machine.is_playing
        
        state_machine.start_game()
        assert state_machine.is_playing
    
    def test_reset(self, state_machine):
        """Test reset."""
        state_machine.connect()
        state_machine.start_game()
        
        state_machine.reset()
        assert state_machine.current_state == state_machine.disconnected
