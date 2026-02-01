"""Parsing and tracking of Nethack game state."""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Position:
    """Player position on the map."""
    x: int
    y: int


@dataclass
class InventoryItem:
    """A single inventory item with metadata."""
    slot: str  # 'a', 'b', 'c', etc.
    name: str  # Item name
    quantity: int = 1  # Number of items in this slot
    identified: bool = True  # Whether we know what this item is
    color: Optional[str] = None  # Color descriptor for unidentified items (e.g., "purple", "red")
    item_type: str = "unknown"  # Type: weapon, armor, potion, scroll, gold, etc.
    ac_value: int = 0  # AC value (lower is better). Extracted from "+2 leather armour" → -2
    is_equipped: bool = False  # Whether this item is currently equipped
    equipment_slot: Optional[str] = None  # Equipment slot: "body", "hands", "feet", "head", "neck" (ring/amulet)


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
    # Inventory tracking
    inventory_items: Dict[str, InventoryItem] = field(default_factory=dict)  # Maps slot to InventoryItem
    # Potion tracking: maps color -> identified effect (e.g., "purple" -> "healing")
    identified_potions: Dict[str, str] = field(default_factory=dict)
    # Unidentified potions: maps slot -> color
    untested_potions: Dict[str, str] = field(default_factory=dict)  # slot -> color
    # Items found on the ground (for pickup)
    items_on_ground: List[Tuple[str, int]] = field(default_factory=list)  # (item_name, quantity)
    # Equipment tracking
    equipped_items: Dict[str, InventoryItem] = field(default_factory=dict)  # equipment_slot -> InventoryItem
    current_ac: int = 10  # Current armor class (lower is better, default ~10)
    
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
        """Check if the game has ended.
        
        Checks for specific game-over messages. Note: "Orb of Zot" appears in the
        opening flavor text ("You feel drawn to the Orb of Zot..."), so we check
        for more specific ending phrases only.
        """
        return any(phrase in output for phrase in [
            'You are dead',
            'You die',
            'You have escaped',
            'Well done!',
            'Congratulations',
            'you have won'  # More specific end-game phrase
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
    
    def parse_inventory_screen(self, screen_text: str) -> Dict[str, InventoryItem]:
        """
        Parse the inventory screen (shown when 'i' command is pressed).
        
        DCSS inventory format:
        a - +0 war axe
        b - a ring of protection
        c - a purple potion
        d - a red potion (unknown)
        
        Args:
            screen_text: The inventory screen text
            
        Returns:
            Dictionary mapping slot letter to InventoryItem
        """
        items = {}
        
        # Remove ANSI codes if present
        clean_text = self._clean_ansi(screen_text) if screen_text else ""
        
        # Parse inventory lines
        # Pattern: slot - item_name
        # Examples:
        # a - +0 war axe
        # b - a ring of protection
        # c - a purple potion
        # d - 42 gold pieces
        # e - a potion of healing (unknown)
        
        inventory_pattern = r'^([a-z])\s*-\s+(.+)$'
        
        for line in clean_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            match = re.match(inventory_pattern, line)
            if not match:
                continue
            
            slot = match.group(1)
            item_desc = match.group(2).strip()
            
            # Parse item description to extract color and type
            item_type = "unknown"
            color = None
            quantity = 1
            identified = True
            ac_value = 0
            is_equipped = False
            equipment_slot = None
            
            # Check for potions
            if 'potion' in item_desc.lower():
                item_type = "potion"
                
                # Check if it's identified or unknown
                if '(unknown)' in item_desc:
                    identified = False
                
                # Extract color if present (e.g., "a purple potion" or "a red potion (unknown)")
                color_match = re.search(r'(purple|red|blue|green|yellow|cyan|magenta|brown|gray|white|black|orange|golden|silver|pink|violet|indigo|turquoise) potion', item_desc.lower())
                if color_match:
                    color = color_match.group(1)
            
            # Check for gold
            elif 'gold' in item_desc.lower():
                item_type = "gold"
                # Extract quantity
                qty_match = re.search(r'(\d+)\s+gold', item_desc.lower())
                if qty_match:
                    quantity = int(qty_match.group(1))
            
            # Check for weapons
            elif any(w in item_desc.lower() for w in ['sword', 'axe', 'mace', 'staff', 'dagger', 'spear', 'polearm', 'club', 'flail']):
                item_type = "weapon"
            
            # Check for armor/jewelry
            elif any(a in item_desc.lower() for a in ['robe', 'armour', 'armor', 'cloak', 'boots', 'gloves', 'helmet', 'shield', 'ring', 'amulet', 'scale', 'mail', 'circlet', 'crown', 'gauntlets', 'sandals', 'necklace', 'tunic', 'leather']):
                item_type = "armor"
            
            # Check for scrolls
            elif 'scroll' in item_desc.lower():
                item_type = "scroll"
                if '(unknown)' in item_desc:
                    identified = False
            
            # Extract AC value from armor items (e.g., "+2 leather armour" → ac_value = -2)
            # Lower AC is better. +2 means 2 points of protection, so AC improves by -2
            if item_type == "armor":
                # Look for +X or -X modifier at the start
                ac_match = re.search(r'([+-])(\d+)', item_desc)
                if ac_match:
                    sign = ac_match.group(1)
                    value = int(ac_match.group(2))
                    # +X protection = -X AC value (better)
                    ac_value = -value if sign == '+' else value
                
                # Detect equipment slot
                desc_lower = item_desc.lower()
                if any(b in desc_lower for b in ['robe', 'armour', 'armor', 'tunic', 'leather', 'scale']):
                    equipment_slot = 'body'
                elif any(g in desc_lower for g in ['gloves', 'gauntlets', 'hands']):
                    equipment_slot = 'hands'
                elif any(f in desc_lower for f in ['boots', 'feet', 'sandals']):
                    equipment_slot = 'feet'
                elif any(h in desc_lower for h in ['helmet', 'helm', 'circlet', 'head', 'crown']):
                    equipment_slot = 'head'
                elif any(n in desc_lower for n in ['ring', 'amulet', 'necklace', 'neck']):
                    equipment_slot = 'neck'
            
            # Create inventory item
            item = InventoryItem(
                slot=slot,
                name=item_desc,
                quantity=quantity,
                identified=identified,
                color=color,
                item_type=item_type,
                ac_value=ac_value,
                is_equipped=is_equipped,
                equipment_slot=equipment_slot
            )
            
            items[slot] = item
            
            # Track untested potions by color
            if item_type == "potion" and not identified and color:
                self.state.untested_potions[slot] = color
        
        # Update game state with inventory
        self.state.inventory_items = items
        
        return items
    
    def parse_ground_items(self, screen_text: str) -> List[Tuple[str, int]]:
        """
        Parse items on the ground from message log.
        
        Looks for patterns like:
        "You see here 10 gold pieces."
        "You see here a purple potion."
        "Things that are here:"
        "a - 10 gold pieces"
        "b - a purple potion"
        
        Args:
            screen_text: Screen text containing ground items
            
        Returns:
            List of (item_name, quantity) tuples
        """
        items_on_ground = []
        
        clean_text = self._clean_ansi(screen_text) if screen_text else ""
        
        # Look for "You see here" pattern
        see_here_pattern = r'You see here (.+?)(?:\.|$)'
        for match in re.finditer(see_here_pattern, clean_text, re.IGNORECASE):
            item_str = match.group(1).strip()
            
            # Extract quantity if present
            qty_match = re.search(r'(\d+)\s+', item_str)
            quantity = int(qty_match.group(1)) if qty_match else 1
            
            items_on_ground.append((item_str, quantity))
        
        # Also look for "Things that are here:" section
        things_pattern = r'Things that are here:(.+?)(?:--more--|$)'
        for section_match in re.finditer(things_pattern, clean_text, re.IGNORECASE | re.DOTALL):
            section = section_match.group(1)
            # Parse each line in this section
            for line in section.split('\n'):
                line = line.strip()
                if not line or line.startswith('-'):
                    continue
                # Format: "a - 10 gold pieces"
                item_match = re.search(r'[a-z]\s*-\s+(.+)', line)
                if item_match:
                    item_str = item_match.group(1).strip()
                    qty_match = re.search(r'(\d+)\s+', item_str)
                    quantity = int(qty_match.group(1)) if qty_match else 1
                    if item_str not in [i[0] for i in items_on_ground]:
                        items_on_ground.append((item_str, quantity))
        
        self.state.items_on_ground = items_on_ground
        
        return items_on_ground    
    def find_better_armor(self) -> Optional[Tuple[str, InventoryItem]]:
        """
        Find armor items in inventory that are better than currently equipped.
        
        Returns better armor based on AC value (lower AC is better).
        Only considers armor items that can be equipped.
        
        Returns:
            Tuple of (slot, item) if better armor found, None otherwise
        """
        better_items = []
        
        for slot, item in self.state.inventory_items.items():
            if item.item_type != 'armor' or not item.equipment_slot:
                continue
            
            # Skip if already equipped
            if item.is_equipped:
                continue
            
            # Check if this item would improve AC
            # In DCSS: lower AC is better. If ac_value is more negative, it's better protection
            if item.ac_value < 0:  # Positive protection
                # Find current equipped item in same slot
                current_equipped = self.state.equipped_items.get(item.equipment_slot)
                if current_equipped and item.ac_value < current_equipped.ac_value:
                    # This item is better (lower AC value)
                    improvement = current_equipped.ac_value - item.ac_value
                    better_items.append((improvement, slot, item))
                elif not current_equipped:
                    # No equipped item in this slot, this is better
                    better_items.append((abs(item.ac_value), slot, item))
        
        if better_items:
            # Sort by improvement (most improvement first)
            better_items.sort(reverse=True, key=lambda x: x[0])
            improvement, best_slot, best_item = better_items[0]
            return (best_slot, best_item)
        
        return None
    
    def get_equipped_ac_total(self) -> int:
        """
        Calculate total AC from all equipped armor items.
        
        Returns:
            Total AC value (lower is better protection)
        """
        total_ac = 0
        for item in self.state.equipped_items.values():
            total_ac += item.ac_value
        return total_ac