"""Enhanced game state machine using python-statemachine framework."""

from enum import Enum
from typing import Optional
from loguru import logger
from statemachine import StateMachine, State


class GameStates(Enum):
    """Game state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    GAMEPLAY = "gameplay"
    MENU = "menu"
    COMBAT = "combat"
    QUIT = "quit"
    ERROR = "error"


class GameStateMachine(StateMachine):
    """
    State machine for DCSS game state using python-statemachine framework.
    
    Tracks game progression from connection through gameplay to exit.
    """
    
    # Define states
    disconnected = State("Disconnected", initial=True)
    connected = State("Connected")
    gameplay = State("Gameplay")
    in_menu = State("Menu")
    in_combat = State("Combat")
    quit_state = State("Quit", final=True)
    error_state = State("Error")
    
    # Transitions
    connect = disconnected.to(connected)
    start_game = connected.to(gameplay)
    enter_menu = gameplay.to(in_menu)
    exit_menu = in_menu.to(gameplay)
    start_combat = gameplay.to(in_combat)
    end_combat = in_combat.to(gameplay)
    quit_game = gameplay.to(quit_state)
    on_error = disconnected.to(error_state) | connected.to(error_state) | gameplay.to(error_state)
    recover = error_state.to(disconnected)
    
    def __init__(self):
        """Initialize the state machine."""
        super().__init__()
        self.previous_state = None
        self.state_history = ["disconnected"]
        self.last_screen = ""
        self.enemy_nearby = False
        self.health_low = False
        
    def update(self, screen_text: str, **context) -> str:
        """
        Update game state based on screen content and context.
        
        Args:
            screen_text: Current screen display
            **context: Additional context (health, enemies, etc.)
            
        Returns:
            Current state as string
        """
        self.last_screen = screen_text.lower()
        previous = self.current_state
        
        # Update context
        if 'enemy_nearby' in context:
            self.enemy_nearby = context['enemy_nearby']
            if self.enemy_nearby and self.current_state == self.gameplay:
                self.start_combat()
        
        if 'health_low' in context:
            self.health_low = context['health_low']
        
        # Detect menu based on screen content
        self._detect_state_change()
        
        # Log transitions
        if previous != self.current_state:
            self.state_history.append(self.current_state.id)
            logger.debug(f"Game state transition: {previous.id} → {self.current_state.id}")
        
        self.previous_state = previous
        return self.current_state.id
    
    def _detect_state_change(self) -> None:
        """Detect state changes from screen content."""
        # Check for quit/exit messages
        if any(text in self.last_screen for text in ["goodbye", "thank you", "quit", "exit"]):
            if self.current_state != self.quit_state:
                self.quit_game()
            return
        
        # Check for error messages
        if any(text in self.last_screen for text in ["error", "fatal", "crash", "exception"]):
            if self.current_state != self.error_state:
                self.on_error()
            return
        
        # Check for menus (multiple choice indicators)
        menu_indicators = ["[a]", "[b]", "[c]", "[y/n]", "please select", "choose"]
        is_menu = any(indicator in self.last_screen for indicator in menu_indicators)
        
        # Check for gameplay content (dungeon view)
        gameplay_indicators = ["exp:", "ac:", "hp:", "mp:", "level", "dungeon"]
        is_gameplay = any(indicator in self.last_screen for indicator in gameplay_indicators)
        
        if is_menu and is_gameplay:
            # In-game menu (inventory, abilities, etc.)
            if self.current_state == self.gameplay:
                self.enter_menu()
        elif not is_menu and is_gameplay:
            # In dungeon playing
            if self.current_state == self.in_menu:
                self.exit_menu()
            elif self.current_state == self.in_combat:
                self.end_combat()
            elif self.current_state != self.gameplay:
                # Recover to gameplay
                pass
    
    @property
    def is_playing(self) -> bool:
        """Check if currently in gameplay."""
        return self.current_state in [self.gameplay, self.in_menu, self.in_combat]
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to game."""
        return self.current_state != self.disconnected
    
    @property
    def is_in_combat(self) -> bool:
        """Check if currently in combat."""
        return self.current_state == self.in_combat
    
    def in_prompt(self) -> bool:
        """Check if in a prompt state."""
        menu_indicators = ["[y/n]", "continue?", "press"]
        return any(indicator in self.last_screen for indicator in menu_indicators)
    
    def in_menu_state(self) -> bool:
        """Check if in menu state (compatibility method)."""
        return self.current_state == self.in_menu or self._is_menu_screen()
    
    def in_gameplay(self) -> bool:
        """Check if in gameplay state."""
        return self.is_playing
    
    def _is_menu_screen(self) -> bool:
        """Check if current screen is a menu."""
        menu_indicators = ["[a]", "[b]", "[c]", "[y/n]", "please select", "choose"]
        return any(indicator in self.last_screen for indicator in menu_indicators)
    
    def reset(self) -> None:
        """Reset to disconnected state."""
        self.current_state = self.disconnected
        self.state_history = ["disconnected"]
        logger.info("Game state machine reset")
    
    def __str__(self) -> str:
        """String representation."""
        return f"GameStateMachine({self.current_state.id})"
