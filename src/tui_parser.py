"""DCSS TUI layout parser - identifies and extracts the 4 main areas of the TUI.

The DCSS TUI has a structured layout with 4 distinct areas:
1. Map (left side): The dungeon layout with player (@) and creatures
2. Character Panel (right side): Stats like Health, Mana, XL, Experience
3. Message Log (bottom): Recent game messages and prompts
4. Encounters (monsters section): List of visible creatures with their symbols

This module identifies the boundaries and content of each area, enabling
more robust and maintainable parsing compared to line-by-line regex.
"""

import re
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from loguru import logger


@dataclass
class TUIArea:
    """Represents a rectangular area of the TUI."""
    name: str
    top: int
    left: int
    bottom: int
    right: int
    content: List[str]  # Lines within this area
    
    @property
    def width(self) -> int:
        return self.right - self.left + 1
    
    @property
    def height(self) -> int:
        return self.bottom - self.top + 1
    
    def get_text(self) -> str:
        """Get all content as a single string."""
        return '\n'.join(self.content)


class DCSSLayoutParser:
    """Parses DCSS TUI layout to identify and extract 4 main areas."""
    
    # Typical DCSS TUI dimensions (160 width × 40 height)
    SCREEN_WIDTH = 160
    SCREEN_HEIGHT = 40
    
    def __init__(self):
        self.map_area: Optional[TUIArea] = None
        self.character_panel: Optional[TUIArea] = None
        self.message_log: Optional[TUIArea] = None
        self.encounters_area: Optional[TUIArea] = None
        self.last_parse_result = {}
    
    def parse_layout(self, screen_text: str) -> Dict[str, TUIArea]:
        """
        Analyze the screen to identify and extract the 4 main TUI areas.
        
        The DCSS TUI layout is typically:
        - Map: Rows 0-22, Columns 0-79 (left side, 80 chars wide)
        - Character Panel: Rows 0-20+, Columns 81-159 (right side)
        - Message Log: Rows 24-39 (bottom section)
        - Encounters: Usually rows 21-24 or part of character panel (monsters list)
        
        Args:
            screen_text: Complete screen text from pyte buffer
            
        Returns:
            Dict with areas: {'map': TUIArea, 'character_panel': TUIArea, 
                            'message_log': TUIArea, 'encounters': TUIArea}
        """
        if not screen_text:
            return {}
        
        lines = screen_text.split('\n')
        areas = {}
        
        # Identify the map area (usually left side, looking for dungeon characters)
        self.map_area = self._extract_map_area(lines)
        if self.map_area:
            areas['map'] = self.map_area
            logger.debug(f"Map area identified: rows {self.map_area.top}-{self.map_area.bottom}, "
                        f"cols {self.map_area.left}-{self.map_area.right}")
        
        # Identify the character panel (usually right side, contains Health:, Mana:, etc.)
        self.character_panel = self._extract_character_panel(lines)
        if self.character_panel:
            areas['character_panel'] = self.character_panel
            logger.debug(f"Character panel identified: rows {self.character_panel.top}-{self.character_panel.bottom}, "
                        f"cols {self.character_panel.left}-{self.character_panel.right}")
        
        # Identify the encounters area (monsters list, usually in rows 21-23)
        self.encounters_area = self._extract_encounters_area(lines)
        if self.encounters_area:
            areas['encounters'] = self.encounters_area
            logger.debug(f"Encounters area identified: rows {self.encounters_area.top}-{self.encounters_area.bottom}, "
                        f"cols {self.encounters_area.left}-{self.encounters_area.right}")
        
        # Identify the message log (bottom rows, usually 24-39)
        self.message_log = self._extract_message_log(lines)
        if self.message_log:
            areas['message_log'] = self.message_log
            logger.debug(f"Message log identified: rows {self.message_log.top}-{self.message_log.bottom}, "
                        f"cols {self.message_log.left}-{self.message_log.right}")
        
        self.last_parse_result = areas
        return areas
    
    def _extract_map_area(self, lines: List[str]) -> Optional[TUIArea]:
        """
        Extract the map area (left side, contains dungeon layout with @ player symbol).
        
        The map is typically:
        - Left-aligned (column 0)
        - 80 characters wide
        - Contains dungeon characters: #.+,|<>(){}[]
        - Contains @ symbol for the player
        """
        # Look for rows that contain dungeon characters like #, ., etc.
        map_content = []
        map_top = None
        map_bottom = None
        
        for row_idx, line in enumerate(lines):
            # Typical map line contains dungeon characters
            if any(char in line[:80] for char in '#.+,-|<>(){}[]@'):
                if map_top is None:
                    map_top = row_idx
                map_bottom = row_idx
                # Extract just the map portion (first 80 chars)
                map_content.append(line[:80] if len(line) >= 80 else line)
        
        if map_top is not None:
            return TUIArea(
                name='map',
                top=map_top,
                left=0,
                bottom=map_bottom,
                right=79,
                content=map_content
            )
        return None
    
    def _extract_character_panel(self, lines: List[str]) -> Optional[TUIArea]:
        """
        Extract the character panel (right side, contains Health:, Mana:, XL:, etc.).
        
        The character panel is typically:
        - Right side starting around column 81
        - Contains lines like "Health: 20/20", "Mana: 5/10", "XL: 3"
        - Appears in rows 0-20+
        """
        # Look for characteristic stat lines
        panel_content = []
        panel_top = None
        panel_bottom = None
        
        for row_idx, line in enumerate(lines):
            # Look for stat keywords in the right portion of the line
            if any(keyword in line for keyword in ['Health:', 'Mana:', 'XL:', 'Time:', 'Exp:']):
                if panel_top is None:
                    panel_top = row_idx
                panel_bottom = row_idx
                # Extract from column 81 onwards (right side)
                panel_line = line[80:] if len(line) > 80 else ''
                panel_content.append(panel_line)
        
        if panel_top is not None:
            return TUIArea(
                name='character_panel',
                top=panel_top,
                left=80,
                bottom=panel_bottom,
                right=159,
                content=panel_content
            )
        return None
    
    def _extract_encounters_area(self, lines: List[str]) -> Optional[TUIArea]:
        """
        Extract the encounters/monsters area (list of visible creatures).
        
        The encounters section is typically:
        - Appears between map and message log (around rows 21-24)
        - Contains creature symbols and names like "g   goblin", "h   hobgoblin"
        - Format: "X   creature_name" where X is the creature symbol
        """
        encounters_content = []
        encounters_top = None
        encounters_bottom = None
        
        # Look for patterns like "g   goblin" (single letter + spaces + name)
        for row_idx, line in enumerate(lines):
            # Skip pure TUI structure lines and empty lines
            if not line.strip() or line.strip().startswith('_'):
                continue
            
            # Look for creature patterns: single letter + multiple spaces + word
            if re.search(r'^[a-zA-Z]\s{3,}\w+', line):
                if encounters_top is None:
                    encounters_top = row_idx
                encounters_bottom = row_idx
                encounters_content.append(line)
        
        if encounters_top is not None and encounters_content:
            return TUIArea(
                name='encounters',
                top=encounters_top,
                left=0,
                bottom=encounters_bottom,
                right=79,
                content=encounters_content
            )
        return None
    
    def _extract_message_log(self, lines: List[str]) -> Optional[TUIArea]:
        """
        Extract the message log (bottom rows with recent game messages).
        
        The message log is typically:
        - Bottom portion of the screen (rows 24-39)
        - Contains game messages like "You see a goblin", "Found 5 gold", etc.
        - May start with "_" separator character
        """
        # Message log is typically in the bottom portion
        # Look for rows that start with "_" (separator) or contain messages
        msg_content = []
        msg_top = None
        msg_bottom = None
        
        for row_idx, line in enumerate(lines):
            # Message lines often start with "_" or contain text
            if line.startswith('_') or (line.strip() and row_idx > 20):
                if msg_top is None:
                    msg_top = row_idx
                msg_bottom = row_idx
                msg_content.append(line)
        
        if msg_top is not None and msg_content:
            return TUIArea(
                name='message_log',
                top=msg_top,
                left=0,
                bottom=msg_bottom,
                right=159,
                content=msg_content
            )
        return None
    
    def get_map_text(self) -> str:
        """Get just the map area as text."""
        return self.map_area.get_text() if self.map_area else ""
    
    def get_character_panel_text(self) -> str:
        """Get just the character panel as text."""
        return self.character_panel.get_text() if self.character_panel else ""
    
    def get_message_log_text(self) -> str:
        """Get just the message log as text."""
        return self.message_log.get_text() if self.message_log else ""
    
    def get_encounters_text(self) -> str:
        """Get just the encounters area as text."""
        return self.encounters_area.get_text() if self.encounters_area else ""
    
    def find_player_position(self) -> Optional[Tuple[int, int]]:
        """
        Find the player (@) position on the map.
        
        Returns:
            Tuple of (x, y) in map coordinates, or None if not found
        """
        if not self.map_area:
            return None
        
        for row_idx, line in enumerate(self.map_area.content):
            if '@' in line:
                col_idx = line.index('@')
                return (col_idx, row_idx)
        return None
    
    def find_creature_symbols_on_map(self) -> List[str]:
        """
        Find all creature symbols visible on the map.
        
        Scans the map for single letters that aren't dungeon features.
        
        Returns:
            List of creature symbol characters found
        """
        if not self.map_area:
            return []
        
        dungeon_chars = set('#.+,-|<>(){}[]@')
        symbols = set()
        
        for line in self.map_area.content:
            for char in line:
                if char.isalpha() and char not in dungeon_chars:
                    symbols.add(char)
        
        return sorted(list(symbols))
