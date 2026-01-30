"""Parsing and tracking of Nethack game state."""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class Position:
    """Player position on the map."""
    x: int
    y: int


@dataclass
class GameState:
    """Representation of the current DCSS game state."""
    position: Optional[Position] = None
    dungeon_branch: str = "Dungeon"
    dungeon_level: int = 1
    health: int = 0
    max_health: int = 0
    mana: int = 0
    max_mana: int = 0
    gold: int = 0
    experience_level: int = 1
    experience_progress: int = 0  # Percentage progress to next level (0-100)
    hunger_level: str = "satisfied"  # DCSS has hunger instead of armor class
    status_line: str = ""
    message_line: str = ""
    inventory: List[str] = None
    visible_map: List[str] = None
    
    def __post_init__(self):
        if self.inventory is None:
            self.inventory = []
        if self.visible_map is None:
            self.visible_map = []


class GameStateParser:
    """Parses PTY output to extract game state by reading current screen snapshot."""

    def __init__(self):
        self.state = GameState()
        self.last_health = (10, 10)  # Default: assume new character starts with some health
        self.last_mana = (0, 0)      # Mana might not exist for all classes
        
        # Initialize state with reasonable defaults for a new character
        self.state.health = 10
        self.state.max_health = 10
        self.state.mana = 0
        self.state.max_mana = 0
        
        # Store the last clean output for reference
        self.last_screen_output = ""

    def parse_output(self, output: str) -> GameState:
        """
        Parse game output (PTY snapshot) to extract game state.
        
        Cleans ANSI codes from the raw output and parses visible text
        to extract game state information.
        
        Args:
            output: Terminal output from Crawl (with ANSI codes)
            
        Returns:
            Updated GameState
        """
        if not output:
            return self.state
            
        # Clean ANSI codes to get readable text
        clean_output = self._clean_ansi(output)
        self.last_screen_output = clean_output
        
        # Parse each line looking for status information
        found_status_in_this_update = False
        for line in clean_output.split('\n'):
            if line.strip():
                found_status_in_this_update = self._parse_line(line.strip()) or found_status_in_this_update
        
        # If we found health in this update, cache it
        if self.state.health > 0 and self.state.max_health > 0:
            self.last_health = (self.state.health, self.state.max_health)
        # If we found mana in this update, cache it
        if self.state.mana >= 0 and self.state.max_mana > 0:
            self.last_mana = (self.state.mana, self.state.max_mana)
        
        # If we didn't find health/mana in this update, restore from cache
        if not found_status_in_this_update:
            if self.last_health:
                self.state.health, self.state.max_health = self.last_health
            if self.last_mana:
                self.state.mana, self.state.max_mana = self.last_mana
        
        return self.state

    def _clean_ansi(self, text: str) -> str:
        """
        Remove ANSI escape sequences from text using regex.
        
        Strips color codes, cursor movement, and other terminal control sequences.
        """
        return re.sub(r'\x1b\[[^\x1b]*?[a-zA-Z]|\x1b\([B0UK]', '', text)

    def _parse_line(self, line: str) -> bool:
        """
        Parse individual output line (already cleaned of ANSI codes).
        
        Returns:
            True if this line contained status information, False otherwise
        """
        if not line or len(line.strip()) < 2:
            return False

        # Status line usually contains player info (level, HP, etc)
        # DCSS format: contains "Health:" or "HP:" with health values
        # Look for common status indicators
        status_indicators = ['Health', 'HP', 'XL:', 'Time:', 'Depth:', 'Dungeon:']
        has_status = any(indicator in line for indicator in status_indicators)
        
        if has_status:
            self._parse_status_line(line)
            return True
        
        # Messages from the game (usually end with punctuation)
        if line.strip().endswith('.') or line.strip().endswith('?'):
            self.state.message_line = line.strip()
        
        return False

    def _parse_status_line(self, line: str) -> None:
        """Parse the status line containing HP, level, dungeon level, etc."""
        # DCSS pattern: Name the Class Level 1 Health 30/30 Magic 10/10 AC 2 Str 10 XL: 1 Next: 0%
        
        # Extract dungeon branch and level (e.g., "D:5" or "Lair:3" or "Dungeon:1")
        branch_match = re.search(r'([A-Za-z]+):(\d+)', line)
        if branch_match:
            self.state.dungeon_branch = branch_match.group(1)
            self.state.dungeon_level = int(branch_match.group(2))
        
        # Extract HP (handle various formats) - MORE LENIENT NOW
        hp_patterns = [
            r'Health[:\s]+(\d+)/(\d+)',  # Health: 23/23 or Health 23/23
            r'HP[:\s]+(\d+)/(\d+)',      # HP: 23/23 or HP 23/23
            r'(\d+)/(\d+)\s+hp',         # 23/23 hp (alternate format)
        ]
        for pattern in hp_patterns:
            hp_match = re.search(pattern, line, re.IGNORECASE)
            if hp_match:
                self.state.health = int(hp_match.group(1))
                self.state.max_health = int(hp_match.group(2))
                logger.debug(f"Parsed health from line: {self.state.health}/{self.state.max_health}")
                break
        
        # Extract Magic/Mana
        mana_patterns = [
            r'Magic\s+(\d+)/(\d+)',
            r'MP[:\s]+(\d+)/(\d+)',
            r'(\d+)/(\d+)\s+mp',
        ]
        for pattern in mana_patterns:
            mana_match = re.search(pattern, line, re.IGNORECASE)
            if mana_match:
                self.state.mana = int(mana_match.group(1))
                self.state.max_mana = int(mana_match.group(2))
                logger.debug(f"Parsed mana from line: {self.state.mana}/{self.state.max_mana}")
                break
        
        # Extract experience level (XL)
        exp_match = re.search(r'XL:\s*(\d+)', line, re.IGNORECASE)
        if exp_match:
            self.state.experience_level = int(exp_match.group(1))
            logger.debug(f"Parsed XL: {self.state.experience_level}")
        
        # Extract experience progress (Next: X%)
        exp_progress_match = re.search(r'Next:\s*(\d+)%', line, re.IGNORECASE)
        if exp_progress_match:
            self.state.experience_progress = int(exp_progress_match.group(1))
        
        # Extract gold
        gold_match = re.search(r'Gold:\s*(\d+)', line, re.IGNORECASE)
        if gold_match:
            self.state.gold = int(gold_match.group(1))
        
        # Extract hunger status
        hunger_keywords = ['engorged', 'full', 'satisfied', 'hungry', 'very hungry', 'near starving', 'starving']
        for hunger in hunger_keywords:
            if hunger in line.lower():
                self.state.hunger_level = hunger
                break
        
        self.state.status_line = line
        logger.debug(f"Parsed status line: {line[:80]}...")

    def get_display_text(self) -> str:
        """
        Get the current terminal display as clean text.
        
        Returns the last parsed screen output without ANSI codes.
        
        Returns:
            Clean text representation of the terminal display
        """
        return self.last_screen_output
    def is_game_ready(self, output: str) -> bool:
        """
        Check if the game is ready for input (has a playable game state displayed).
        
        Checks for gameplay indicators including health status, experience level,
        or the player character on the map.
        """
        if not output:
            return False
        
        # Clean ANSI codes and check for game indicators
        clean_output = self._clean_ansi(output)
        
        # Check for basic gameplay indicators
        has_status = any(marker in clean_output for marker in [
            'HP:', 'Health:',  # Health indicator
            'XL:', 'Dungeon',  # Game state
            'AC:', 'EV:',  # Armor/Evasion
        ])
        
        # Also check for player character on map (@)
        has_map = '@' in clean_output
        
        return has_status or has_map  # Either status or map indicates gameplay

    def is_game_over(self, output: str) -> bool:
        """Check if the game has ended."""
        return any(phrase in output for phrase in [
            'You are dead',
            'You die',
            'You have escaped',
            'Well done!',
            'Congratulations',
            'Orb of Zot'
        ])
    
    def has_level_up_message(self, output: str) -> bool:
        """
        Check if the screen contains a level-up message.
        
        When the player gains a level, DCSS displays "You have reached level X!"
        This method detects that message to handle level-up events specially.
        
        Args:
            output: Game output to check
            
        Returns:
            True if a level-up message is present
        """
        return 'You have reached level' in output or 'You reach level' in output
    
    def extract_level_from_message(self, output: str) -> Optional[int]:
        """
        Extract the new level number from a level-up message.
        
        Searches for "You have reached level X!" pattern and extracts X.
        
        Args:
            output: Game output containing level-up message
            
        Returns:
            The new experience level, or None if not found
        """
        match = re.search(r'You have reached level (\d+)', output)
        if not match:
            match = re.search(r'You reach level (\d+)', output)
        
        if match:
            return int(match.group(1))
        return None
