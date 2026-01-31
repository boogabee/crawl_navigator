"""Enhanced character creation state machine using python-statemachine framework."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
import re
from loguru import logger
from statemachine import StateMachine, State


class CharCreationStates(Enum):
    """Character creation states."""
    STARTUP = "startup"
    START = "start"
    SPECIES = "species"
    CLASS = "class"
    BACKGROUND = "background"
    SKILLS = "skills"
    ABILITIES = "abilities"
    DIFFICULTY = "difficulty"
    CONFIRMATION = "confirmation"
    GAMEPLAY = "gameplay"
    ERROR = "error"


@dataclass
class MenuTransitionPattern:
    """Pattern for detecting state transitions."""
    patterns: List[str]
    is_regex: bool = False
    case_sensitive: bool = False
    match_all: bool = False  # If True, ALL patterns must match. If False, ANY pattern matching is sufficient.
    
    def matches(self, text: str) -> bool:
        """Check if text matches pattern(s).
        
        If match_all=False (default): Returns True if ANY pattern matches (OR logic)
        If match_all=True: Returns True only if ALL patterns match (AND logic)
        """
        test_text = text if self.case_sensitive else text.lower()
        
        if self.match_all:
            # AND logic: all patterns must match
            for pattern in self.patterns:
                pattern_to_check = pattern if self.case_sensitive else pattern.lower()
                
                if self.is_regex:
                    if not re.search(pattern_to_check, test_text):
                        return False
                else:
                    if pattern_to_check not in test_text:
                        return False
            
            return True
        else:
            # OR logic: any pattern matching is sufficient
            for pattern in self.patterns:
                pattern_to_check = pattern if self.case_sensitive else pattern.lower()
                
                if self.is_regex:
                    if re.search(pattern_to_check, test_text):
                        return True
                else:
                    if pattern_to_check in test_text:
                        return True
            
            return False


class CharacterCreationStateMachine(StateMachine):
    """
    State machine for character creation using python-statemachine framework.
    
    Automates navigation through DCSS character creation menus using state transitions
    triggered by screen text detection.
    """
    
    # Define states
    startup = State("Startup Menu", initial=True)
    species = State("Species Selection")
    class_select = State("Class Selection")
    background = State("Background Selection")
    skills = State("Skills Selection")
    abilities = State("Abilities Selection")
    difficulty = State("Difficulty Selection")
    confirmation = State("Confirmation")
    gameplay = State("Gameplay Ready", final=True)
    error = State("Error")
    
    # Transitions from STARTUP
    startup_to_species = startup.to(species)
    startup_error = startup.to(error)
    
    # Transitions from START (removed - startup is now initial)
    
    # Transitions from SPECIES
    species_to_class = species.to(class_select)
    species_to_background = species.to(background)
    species_to_gameplay = species.to(gameplay)
    species_error = species.to(error)
    
    # Transitions from CLASS
    class_to_background = class_select.to(background)
    class_to_skills = class_select.to(skills)
    class_to_gameplay = class_select.to(gameplay)
    class_error = class_select.to(error)
    
    # Transitions from BACKGROUND
    background_to_skills = background.to(skills)
    background_to_abilities = background.to(abilities)
    background_to_difficulty = background.to(difficulty)
    background_to_gameplay = background.to(gameplay)
    background_error = background.to(error)
    
    # Transitions from SKILLS
    skills_to_abilities = skills.to(abilities)
    skills_to_difficulty = skills.to(difficulty)
    skills_to_gameplay = skills.to(gameplay)
    skills_error = skills.to(error)
    
    # Transitions from ABILITIES
    abilities_to_difficulty = abilities.to(difficulty)
    abilities_to_confirmation = abilities.to(confirmation)
    abilities_to_gameplay = abilities.to(gameplay)
    abilities_error = abilities.to(error)
    
    # Transitions from DIFFICULTY
    difficulty_to_confirmation = difficulty.to(confirmation)
    difficulty_to_gameplay = difficulty.to(gameplay)
    difficulty_error = difficulty.to(error)
    
    # Transitions from CONFIRMATION
    confirmation_to_gameplay = confirmation.to(gameplay)
    confirmation_error = confirmation.to(error)
    
    # Recovery from error
    error_retry = error.to(species)
    
    def __init__(self):
        """Initialize the state machine."""
        super().__init__()
        self.screen_text = ""
        self.stuck_count = 0
        self.max_stuck_threshold = 3
        self.last_state = None
        self.state_history = ["start"]
        self.transition_patterns = self._build_patterns()
        
    def _build_patterns(self) -> dict:
        """Build detection patterns for state transitions.
        
        Order matters! Check more specific patterns first to avoid catching generic strings.
        """
        # Return as list of tuples (ordered) rather than dict to control matching order
        # Most specific patterns first, general patterns last
        return {
            # Most specific: gameplay indicators (requires ALL of: HP, AC, XL on the same line or multiple lines)
            # Use match_all=True to require all three indicators to be present
            CharCreationStates.GAMEPLAY: MenuTransitionPattern(
                [r"hp:\s+\d+/\d+", r"ac:\s+\d+", r"ev:\s+\d+"],
                is_regex=True,
                case_sensitive=False,
                match_all=True  # ALL three indicators must be present to detect gameplay
            ),
            # Character creation menus (more specific)
            CharCreationStates.SPECIES: MenuTransitionPattern(
                ["select your species", "select your ancestry", "choose.*race", "choose.*species", "which.*race", "please select your species"],
                is_regex=True,
                case_sensitive=False
            ),
            CharCreationStates.CLASS: MenuTransitionPattern(
                ["select your class", "choose.*class", "job.*:", "profession.*:", "which.*class", "please select your class"],
                is_regex=True,
                case_sensitive=False
            ),
            CharCreationStates.BACKGROUND: MenuTransitionPattern(
                ["select your background", "please select your background", "choose.*background", "religious.*choice"],
                is_regex=True,
                case_sensitive=False
            ),
            CharCreationStates.SKILLS: MenuTransitionPattern(
                ["choose.*skill", "select.*skill", "skill.*point", "skill.*aptitude", "choice.*weapon", "select.*weapon"],
                is_regex=True,
                case_sensitive=False
            ),
            CharCreationStates.ABILITIES: MenuTransitionPattern(
                ["ability", "ability.*score", "abil.*:", "select.*ability"],
                is_regex=True,
                case_sensitive=False
            ),
            CharCreationStates.DIFFICULTY: MenuTransitionPattern(
                ["difficulty", "challenge", "permadeath"],
                is_regex=True,
                case_sensitive=False
            ),
            # Least specific: startup (generic strings that could appear anywhere)
            CharCreationStates.STARTUP: MenuTransitionPattern(
                ["enter your name:", "choose game seed", "tutorial", "hints mode", "dungeon sprint"],
                is_regex=False,
                case_sensitive=False
            ),
        }
    
    def update(self, screen_text: str) -> str:
        """
        Process screen output and update state.
        
        Args:
            screen_text: Current screen content
            
        Returns:
            Current state as string
        """
        self.screen_text = screen_text.lower()
        previous = self.current_state
        
        # Detect stuck condition
        if self.last_state == self.current_state:
            self.stuck_count += 1
        else:
            self.stuck_count = 0
        
        # Try to trigger transitions based on screen content
        self._process_screen()
        
        # Log state change
        if previous != self.current_state:
            self.state_history.append(self.current_state.id)
            logger.debug(f"State transition: {previous.id} → {self.current_state.id}")
        
        self.last_state = self.current_state
        return self.current_state.id
    
    def _process_screen(self) -> None:
        """Process screen and trigger appropriate transitions.
        
        CRITICAL: Once in GAMEPLAY state, don't allow backward transitions to menus.
        Backward transitions only occur if we explicitly detect startup/menu patterns.
        """
        # If we're in gameplay, don't downgrade to menus
        # Only allow forward transitions to gameplay or error recovery
        if self.current_state == self.gameplay:
            # Stay in gameplay unless we explicitly detect startup/menu patterns
            # This prevents false downgrades when HUD display changes
            return
        
        # For non-gameplay states, check what state we should be in based on screen content
        for target_state, pattern in self.transition_patterns.items():
            if pattern.matches(self.screen_text):
                logger.debug(f"Pattern matched for {target_state}")
                self._trigger_transition(target_state)
                break
    
    def _trigger_transition(self, target_state: CharCreationStates) -> None:
        """Trigger appropriate transition to target state."""
        if target_state == CharCreationStates.STARTUP and self.current_state == self.startup:
            pass  # Already in startup, wait for user input
        elif target_state == CharCreationStates.SPECIES:
            if self.current_state == self.startup:
                self.startup_to_species()
            elif self.current_state == self.species:
                pass  # Already in race
        elif target_state == CharCreationStates.CLASS:
            if self.current_state == self.species:
                self.species_to_class()
            elif self.current_state == self.class_select:
                pass  # Already in class
        elif target_state == CharCreationStates.BACKGROUND:
            if self.current_state == self.species:
                self.species_to_background()
            elif self.current_state == self.class_select:
                self.class_to_background()
            elif self.current_state == self.background:
                pass  # Already in background
        elif target_state == CharCreationStates.SKILLS:
            if self.current_state == self.class_select:
                self.class_to_skills()
            elif self.current_state == self.background:
                self.background_to_skills()
        elif target_state == CharCreationStates.ABILITIES:
            if self.current_state == self.background:
                self.background_to_abilities()
            elif self.current_state == self.skills:
                self.skills_to_abilities()
        elif target_state == CharCreationStates.DIFFICULTY:
            if self.current_state == self.background:
                self.background_to_difficulty()
            elif self.current_state == self.skills:
                self.skills_to_difficulty()
            elif self.current_state == self.abilities:
                self.abilities_to_difficulty()
        elif target_state == CharCreationStates.GAMEPLAY:
            # Can transition to gameplay from multiple states
            if self.current_state in [self.species, self.class_select, self.background, 
                                     self.skills, self.abilities, self.difficulty, self.confirmation]:
                if self.current_state == self.species:
                    self.species_to_gameplay()
                elif self.current_state == self.class_select:
                    self.class_to_gameplay()
                elif self.current_state == self.background:
                    self.background_to_gameplay()
                elif self.current_state == self.skills:
                    self.skills_to_gameplay()
                elif self.current_state == self.abilities:
                    self.abilities_to_gameplay()
                elif self.current_state == self.difficulty:
                    self.difficulty_to_gameplay()
                elif self.current_state == self.confirmation:
                    self.confirmation_to_gameplay()
    
    @property
    def is_stuck(self) -> bool:
        """Check if stuck in same state."""
        return self.stuck_count >= self.max_stuck_threshold
    
    @property
    def in_gameplay(self) -> bool:
        """Check if character is ready for gameplay."""
        return self.current_state == self.gameplay
    
    def reset(self) -> None:
        """Reset state machine to startup."""
        self.current_state = self.startup
        self.stuck_count = 0
        self.state_history = ["startup"]
        logger.info("Character creation state machine reset")
    
    def __str__(self) -> str:
        """String representation of state machine."""
        return f"CharCreationStateMachine({self.current_state.id}, stuck={self.is_stuck})"
