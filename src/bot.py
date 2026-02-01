"""Main bot logic for playing Dungeon Crawl Stone Soup."""

import time
import re
from typing import Optional, Tuple
from datetime import datetime
import os
import pyte
import random
import string
from loguru import logger

from src.local_client import LocalCrawlClient
from src.game_state import GameStateParser
from src.state_machines.game_state_machine import GameStateMachine
from src.state_machines.char_creation_state_machine import CharacterCreationStateMachine
from src.display.bot_unified_display import UnifiedBotDisplay
from src.decision_engine import DecisionEngine, DecisionContext, create_default_engine
from src.tui_parser import DCSSLayoutParser


class ScreenBuffer:
    """
    Terminal screen buffer using pyte for accurate ANSI code parsing.
    
    PRIMARY SOURCE OF GAME STATE: The pyte buffer is the authoritative, complete game state.
    Raw PTY output contains only ANSI code DELTAS (incremental changes), not complete text.
    This buffer ACCUMULATES all deltas into a 160x40 character grid for the complete picture.
    
    Used for BOTH visual screen capture AND game state decisions (not just screenshots!).
    All game logic should use get_screen_text() to read the complete reconstructed state.
    """
    
    def __init__(self, width: int = 160, height: int = 40):
        """Initialize screen buffer with pyte terminal emulator."""
        self.width = width
        self.height = height
        self.screen = pyte.Screen(width, height)
        self.stream = pyte.Stream(self.screen)
    
    def update_from_output(self, output: str) -> None:
        """
        Update screen buffer from PTY output (with ANSI codes).
        
        Args:
            output: Raw PTY output with ANSI escape sequences
        """
        try:
            self.stream.feed(output)
        except Exception as e:
            logger.debug(f"pyte parsing error: {e}")
    
    def get_screen_text(self) -> str:
        """Get the current screen as text."""
        lines = []
        for line in self.screen.display:
            # Remove trailing spaces from each line
            lines.append(line.rstrip())
        # Remove trailing empty lines
        while lines and not lines[-1]:
            lines.pop()
        return '\n'.join(lines)


class DCSSBot:
    """Main bot for playing Dungeon Crawl Stone Soup."""

    def __init__(self, crawl_command: str = None):
        """
        Initialize the bot.
        
        Args:
            crawl_command: Command to run local Crawl (defaults to /usr/games/crawl)
        """
        # Initialize local Crawl client
        logger.info("Using LOCAL execution mode")
        self.local_client = LocalCrawlClient(crawl_command=crawl_command or '/usr/games/crawl')
        
        self.parser = GameStateParser()
        self.state_tracker = GameStateMachine()
        self.char_creation_state = CharacterCreationStateMachine()
        self.move_count = 0
        self.max_steps = 0  # Will be set when run() is called
        self.last_screen = ""
        self.last_action = "Initializing..."
        self.action_reason = ""  # Reason for the last action sent
        self.capture_all_screens = True  # Capture all screens during character creation for debugging
        
        # Screen buffer for caching complete screen state
        self.screen_buffer = ScreenBuffer()
        
        # Unified display (game screen + activity panel)
        self.unified_display = UnifiedBotDisplay()
        
        # Track consecutive rest actions to prevent infinite resting
        self.consecutive_rest_actions = 0
        self.max_consecutive_rests = 5  # After 5 rests, force exploration even if damaged
        
        # Track last action to prevent invalid command sequences
        self.last_action_sent = ""  # Last actual command sent to game
        
        # Cache last known health values (used when status updates don't include health)
        self.last_known_health = 0
        self.last_known_max_health = 0
        
        # Once gameplay starts, assume we stay in gameplay
        # (State machine may not track properly with delta updates)
        self.gameplay_started = False
        
        # Track experience gained during session
        self.initial_experience_level = 0
        self.initial_experience_progress = 0
        self.final_experience_level = 0
        self.final_experience_progress = 0
        
        # Capture final game state before quitting (parser.state gets reset by quit screens)
        self.final_health = 0
        self.final_max_health = 0
        self.final_mana = 0
        self.final_max_mana = 0
        self.final_gold = 0
        self.final_location = ""
        
        # Track goto command state for descending levels
        # States: None -> 'awaiting_location_type' -> 'awaiting_level_number' -> None
        self.goto_state = None  # None, 'awaiting_location_type', or 'awaiting_level_number'
        self.goto_target_level = 0
        
        # Track unchanged screens to detect errors
        self.unchanged_screen_count = 0
        self.max_unchanged_screens = 5  # Error if screen doesn't change 5 times in a row
        
        # Event tracking for exploration log
        self.exploration_events = []  # List of (move_count, event_type, description)
        self.gold_found = 0
        self.items_found = []
        self.enemies_encountered = set()
        self.level_ups_gained = []
        self.last_level_up_processed = 0  # Track last level we processed level-up for (avoid re-detecting same message)
        self.last_attribute_increase_level = 0  # Track level we processed attribute increase for (avoid re-prompting)
        
        # Inventory and item tracking
        self.quaff_slot = None  # Current slot being quaffed (set by _identify_untested_potions)
        self.last_items_on_ground_check = 0  # Move count when we last checked for items
        self.last_grab_attempt = 0  # Move count when we last tried to grab items
        self.last_grab_failed = False  # Whether the last grab attempt found nothing
        self.inventory_stale = True  # Whether our inventory cache needs refreshing
        self.last_inventory_refresh = 0  # Move count when we last refreshed inventory
        self.in_inventory_screen = False  # Whether we're currently viewing inventory
        self.in_item_pickup_menu = False  # Whether we're in the "Pick up what?" menu
        
        # Equipment management
        self.equip_slot = None  # Current slot being equipped (set by _find_and_equip_better_armor)
        self.last_equipment_check = 0  # Move count when we last checked for equipment upgrades
        
        # Initialize decision engine (Phase 3 refactor: replaces 1200-line _decide_action method)
        self.decision_engine = create_default_engine()
        
        # Feature flag for Phase 3b migration: use engine vs legacy implementation
        # Set via --use-engine command-line flag or programmatically
        self.use_decision_engine = False
        
        # Phase 3b migration tracking
        self.engine_decisions_made = 0
        self.legacy_fallback_count = 0
        self.decision_divergences = 0
        
        # Initialize log file
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(logs_dir, f"bot_session_{timestamp}.log")
        
        # Configure file logging with loguru

        logger.add(self.log_file, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}")
        
        # Initialize debug screens directory
        self.debug_screens_dir = os.path.join(logs_dir, f"screens_{timestamp}")
        os.makedirs(self.debug_screens_dir, exist_ok=True)
        self.screen_counter = 0
        self.screen_index_file = os.path.join(self.debug_screens_dir, "index.txt")
        
        # Write header to log file
        with open(self.log_file, 'w') as f:
            f.write(f"=== DCSS Bot Session Log ===\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Mode: LOCAL (Dungeon Crawl Stone Soup)\n")
            f.write(f"Debug screens directory: {self.debug_screens_dir}\n")
            f.write("=" * 80 + "\n\n")
        
        # Initialize screen index
        with open(self.screen_index_file, 'w') as f:
            f.write("=== Screen Interactions Index ===\n")
            f.write(f"Session started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

    def _clean_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from text."""
        # Remove all ANSI escape sequences including:
        # - Color/style codes: \x1b[...m
        # - Cursor movement: \x1b[...H, \x1b[...d, etc
        # - Character set selection: \x1b(B, etc
        return re.sub(r'\x1b\[[^\x1b]*?[a-zA-Z]|\x1b\([B0UK]', '', text)

    def _generate_random_name(self, length: int = None) -> str:
        """Generate a random character name (6-8 characters by default)."""
        if length is None:
            length = random.randint(6, 8)
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    def _log_event(self, event_type: str, description: str) -> None:
        """
        Log an exploration event.
        
        Args:
            event_type: Type of event (gold, item, enemy, poi, level_up, etc)
            description: Description of the event
        """
        event = (self.move_count, event_type, description)
        self.exploration_events.append(event)
        logger.info(f"[Event] Move #{self.move_count}: [{event_type.upper()}] {description}")

    def _detect_exploration_events(self, output: str) -> None:
        """
        Detect and log exploration events from the game output.
        
        Looks for messages like:
        - "Found X gold pieces"
        - "You see X"
        - "You encounter X"
        - Various discovery messages
        
        Args:
            output: Game output to scan for events
        """
        if not output:
            return
        
        clean_output = self._clean_ansi(output)
        
        # Gold detection
        gold_match = re.search(r'Found (\d+) gold pieces?', clean_output)
        if gold_match:
            amount = int(gold_match.group(1))
            self.gold_found += amount
            self._log_event('gold', f"Found {amount} gold pieces")
            return  # Process one event per screen
        
        # Item detection
        item_patterns = [
            (r'You see (.+?)\.', 'discovered'),
            (r'There is (.+?) here', 'found'),
        ]
        for pattern, event_type in item_patterns:
            item_match = re.search(pattern, clean_output)
            if item_match:
                item = item_match.group(1)
                if item not in self.items_found:
                    self.items_found.append(item)
                    self._log_event('item', f"{event_type.title()}: {item}")
                return
        
        # Enemy encounter detection
        enemy_patterns = [
            r'You encounter (.+?)(?:\.|,)',
            r'There is (.+?) here',
        ]
        for pattern in enemy_patterns:
            enemy_match = re.search(pattern, clean_output)
            if enemy_match:
                enemy = enemy_match.group(1).strip()
                # Filter out items and focus on creatures
                if any(creature in enemy.lower() for creature in [
                    'rat', 'bat', 'spider', 'goblin', 'kobold', 'orc', 'troll',
                    'endoplasm', 'slug', 'newt', 'iguana', 'ape', 'giant',
                    'ogre', 'dragon', 'demon', 'ghost', 'mummy'
                ]):
                    if enemy not in self.enemies_encountered:
                        self.enemies_encountered.add(enemy)
                        self._log_event('enemy', f"Encountered: {enemy}")
                    return
        
        # Level-up detection (already logged separately, but add to events too)
        # Use TUI parser to extract message log section for reliability
        screen_text = self.screen_buffer.get_screen_text() if self.last_screen else ""
        if screen_text:
            tui_parser = DCSSLayoutParser()
            tui_areas = tui_parser.parse_layout(screen_text)
            message_log_area = tui_areas.get('message_log', None)
            if message_log_area:
                message_content = message_log_area.get_text()
                if 'You have reached level' in message_content:
                    level_match = re.search(r'You have reached level (\d+)', message_content)
                    if level_match:
                        level = int(level_match.group(1))
                        if level not in self.level_ups_gained:
                            self.level_ups_gained.append(level)
                            # Note: This will be logged by the main level-up detection too
                    return
        
        # Door/Feature discovery
        feature_patterns = [
            (r'open door', 'door'),
            (r'closed door', 'door'),
            (r'stone staircase', 'stairs'),
            (r'metal grate', 'grate'),
        ]
        for pattern, feature_type in feature_patterns:
            if pattern in clean_output:
                self._log_event('feature', f"Found {feature_type}")
                return

    def _get_screen_capture(self) -> str:
        """
        Get the full visible PTY screen from accumulated PTY output.
        
        Returns:
            The visual screen as it appears (ANSI codes cleaned for readability)
        """
        try:
            # Use screen buffer to get accumulated visual state
            visual = self.screen_buffer.get_screen_text()
            
            # If buffer is mostly empty, fall back to showing cleaned last_screen
            if not visual.strip():
                return self._clean_ansi(self.last_screen) if self.last_screen else "(empty)"
            
            return visual
        except Exception as e:
            logger.error(f"Failed to get screen capture: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"(Screen capture error: {e})"

    def _display_tui_to_user(self, action: str = "") -> None:
        """
        Display the current TUI state to the user in real-time.

        Shows the FULL accumulated screen state from the pyte buffer with a bot activity panel.
        This is the complete visual representation of what the bot sees.
        
        Args:
            action: Description of what the bot is doing (e.g., "Entering gameplay")
        """
        try:
            # Get the FULL accumulated visual screen state from the pyte buffer
            visual_screen = self.screen_buffer.get_screen_text()
            
            if not visual_screen or not visual_screen.strip():
                logger.debug("No visual screen available to display")
                return
            
            # Build status/health info
            state = self.parser.state
            status_parts = []
            
            # Only display health if we've actually parsed it from the game screen
            # (i.e., the screen contains "Health:" or "HP:" text indicating we're in gameplay)
            if 'Health:' in visual_screen or 'HP:' in visual_screen:
                if state.health > 0 or state.max_health > 0:
                    status_parts.append(f"Health: {state.health}/{state.max_health}")
                if state.mana > 0 or state.max_mana > 0:
                    status_parts.append(f"Mana: {state.mana}/{state.max_mana}")
            
            # Display level and dungeon depth if available
            if state.experience_level > 0:
                status_parts.append(f"Level: {state.experience_level}")
            if state.dungeon_level > 0:
                status_parts.append(f"Depth: {state.dungeon_branch}:{state.dungeon_level}")
            
            # Display step progress
            if self.max_steps > 0:
                status_parts.append(f"Steps: {self.move_count}/{self.max_steps}")
            elif self.move_count > 0:
                status_parts.append(f"Steps: {self.move_count}")
            
            health_info = " | ".join(status_parts)
            
            # Get current state - handle both state machine types
            try:
                # Try to get state name from state_tracker (GameStateMachine from python-statemachine)
                current_state = self.state_tracker.current_state.id if self.state_tracker.current_state else "UNKNOWN"
            except (AttributeError, TypeError):
                current_state = "UNKNOWN"
            
            # Display using unified display
            self.unified_display.display(
                visual_screen=visual_screen,
                move_count=self.move_count,
                action=action or self.last_action,
                state=current_state,
                health=health_info
            )
            
        except Exception as e:
            logger.debug(f"Error displaying TUI: {e}")
    
    def _log_activity(self, message: str, level: str = "info") -> None:
        """
        Log an activity message to the unified display panel.
        
        Args:
            message: Activity message
            level: Message level - "info", "debug", "warning", "error", "success"
        """
        try:
            self.unified_display.add_activity(message, level)
        except Exception as e:
            logger.debug(f"Error logging activity: {e}")

    def _save_debug_screen(self, screen: str, action: str) -> str:
        """
        Save a debug screen capture with action context.
        
        Saves both raw ANSI and cleaned versions, and updates index.
        Also captures the full visual screen state from the screen buffer.
        
        Args:
            screen: The game screen content (with ANSI codes)
            action: The action being performed or description
            
        Returns:
            The filename where the screen was saved
        """
        try:
            self.screen_counter += 1
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Create numbered filenames
            screen_num = f"{self.screen_counter:04d}"
            raw_file = f"{screen_num}_raw.txt"
            clean_file = f"{screen_num}_clean.txt"
            visual_file = f"{screen_num}_visual.txt"
            raw_path = os.path.join(self.debug_screens_dir, raw_file)
            clean_path = os.path.join(self.debug_screens_dir, clean_file)
            visual_path = os.path.join(self.debug_screens_dir, visual_file)
            
            # Get the full visual screen from buffer
            visual_screen = self._get_screen_capture()
            
            # Save raw screen with ANSI codes
            with open(raw_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Screen #{self.screen_counter} ===\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Move: #{self.move_count}\n")
                f.write(f"Action: {action}\n")
                f.write("=" * 80 + "\n\n")
                f.write(screen)
            
            # Save cleaned screen (no ANSI codes)
            clean_screen = self._clean_ansi(screen)
            with open(clean_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Screen #{self.screen_counter} (Cleaned Delta) ===\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Move: #{self.move_count}\n")
                f.write(f"Action: {action}\n")
                f.write("=" * 80 + "\n\n")
                
                # Format cleaned screen with visible borders for clarity
                lines = clean_screen.split('\n')
                f.write("┌" + "─" * 78 + "┐\n")
                for line in lines:
                    # Pad or truncate to 78 chars
                    line = line.ljust(78)[:78]
                    f.write("│ " + line + " │\n")
                f.write("└" + "─" * 78 + "┘\n")
            
            # Save visual screen (accumulated state from buffer)
            with open(visual_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Screen #{self.screen_counter} (Full Visual State) ===\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Move: #{self.move_count}\n")
                f.write(f"Action: {action}\n")
                f.write("=" * 80 + "\n\n")
                
                # Format visual screen with visible borders
                lines = visual_screen.split('\n')
                f.write("┌" + "─" * 118 + "┐\n")
                for line in lines:
                    # Pad or truncate to 118 chars to show full game screen
                    line = line.ljust(118)[:118]
                    f.write("│" + line + "│\n")
                f.write("└" + "─" * 118 + "┘\n")
            
            # Update index file
            try:
                with open(self.screen_index_file, 'a') as f:
                    f.write(f"[{self.screen_counter:04d}] Move #{self.move_count} at {timestamp}\n")
                    f.write(f"        Action: {action}\n")
                    f.write(f"        Raw: {raw_file} ({len(screen)} bytes)\n")
                    f.write(f"        Clean: {clean_file} ({len(clean_screen)} chars)\n")
                    f.write(f"        Visual: {visual_file}\n")
                    f.write("\n")
            except Exception as e:
                logger.debug(f"Failed to update screen index: {e}")
            
            return visual_file
        
        except Exception as e:
            logger.error(f"Failed to save debug screen #{self.screen_counter}: {e}")
            logger.error(f"  Debug dir: {self.debug_screens_dir}")
            logger.error(f"  Action: {action}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            return ""

    def _log_screen_and_action(self, screen: str, action: str) -> None:
        """
        Log the current screen state and the action being taken.
        
        Args:
            screen: The game screen content
            action: The action being performed
        """
        try:
            with open(self.log_file, 'a') as f:
                # Write timestamp and move number
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                f.write(f"[{timestamp}] Move #{self.move_count}\n")
                f.write(f"Action: {action}\n")
                f.write("-" * 80 + "\n")
                
                # Write the cleaned screen content
                clean_screen = self._clean_ansi(screen)
                f.write("SCREEN:\n")
                f.write(clean_screen)
                f.write("\n")
                f.write("=" * 80 + "\n\n")
                
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")

    def _detect_menu_type(self, screen: str) -> str:
        """
        Detect what type of menu is currently displayed.
        
        Args:
            screen: Screen content
            
        Returns:
            Menu type ('race', 'class', 'background', 'weapons', 'skills', 'difficulty', 'abilities', 'unknown')
        """
        clean = self._clean_ansi(screen).lower()
        
        # First check if this looks like a game state, not a menu
        # Game states have dungeon map elements
        if '@' in screen and any(char in screen for char in ['#', '+', '.', ' ']):
            # This looks like a dungeon map with the player character
            if any(word in clean for word in ['exp:', 'ac:', 'hp:', '@']):
                return 'unknown'  # This is the game, not a menu
        
        # Now check for specific menus - use the actual DCSS menu text
        if any(phrase in clean for phrase in ['select your species', 'select your ancestry', 'please select your species',
                                                'choose your race', 'choose your species', 'species:', 'ancestry:', 
                                                'which species', 'which ancestry', 'which race']):
            return 'race'
        elif any(phrase in clean for phrase in ['select your class', 'please select your class',
                                                  'choose your class', 'job:', 'profession:', 'which class', 
                                                  'which job', 'choose your job']):
            return 'class'
        elif any(phrase in clean for phrase in ['choice of weapons', 'choice of melee weapons', 'choice of ranged weapons',
                                                  'weapon choice']):
            return 'weapons'
        elif any(phrase in clean for phrase in ['select your background', 'please select your background',
                                                  'background:', 'background -', 'choose background', 
                                                  'religious choice']):
            return 'background'
        elif any(phrase in clean for phrase in ['skill aptitudes', 'skill -', 'skill points', 'choose skills',
                                                  'select your skills']):
            return 'skills'
        elif any(phrase in clean for phrase in ['difficulty', 'challenge', 'permadeath', 'hardcore',
                                                  'select your difficulty']):
            return 'difficulty'
        elif any(phrase in clean for phrase in ['ability', 'ability -', 'abil:', 'ability scores',
                                                  'select your ability']):
            return 'abilities'
        
        return 'unknown'
    
    def _choose_menu_option(self, screen: str, menu_type: str) -> str:
        """
        Choose an option from a menu.
        
        Args:
            screen: Screen content
            menu_type: Type of menu detected
            
        Returns:
            Command to send (single character)
        """
        clean = self._clean_ansi(screen).lower()
        
        # Character preferences
        # Race: Gnoll
        # Class: Fighter  
        # Weapon: War Axe
        
        if menu_type == 'race':
            # Prefer Gnoll
            if 'gnoll' in clean:
                logger.info("Menu: Choosing Gnoll (g)")
                return 'g'
            elif 'human' in clean:
                logger.info("Menu: Choosing Human (h) - Gnoll not available")
                return 'h'
            else:
                logger.info("Menu: Choosing first race option (a)")
                return 'a'
        
        elif menu_type == 'class':
            # Always choose Fighter
            if 'fighter' in clean:
                logger.info("Menu: Choosing Fighter (f)")
                return 'f'
            else:
                logger.info("Menu: Choosing first class option (a)")
                return 'a'
        
        elif menu_type == 'background':
            # Choose first option (background doesn't matter much)
            logger.info("Menu: Choosing default option for background (a)")
            return 'a'
        
        elif menu_type == 'weapons':
            # Prefer War Axe
            if 'war axe' in clean:
                logger.info("Menu: Choosing War Axe (w)")
                return 'w'
            elif 'axe' in clean:
                logger.info("Menu: Choosing Axe (a)")
                return 'a'
            else:
                logger.info("Menu: Choosing first weapon option (a)")
                return 'a'
        
        elif menu_type == 'skills':
            # Choose first skill option
            logger.info("Menu: Choosing default option for skills (a)")
            return 'a'
        
        elif menu_type == 'abilities':
            # Choose first ability option
            logger.info("Menu: Choosing default option for abilities (a)")
            return 'a'
        
        elif menu_type == 'difficulty':
            # Choose first difficulty option (Normal)
            logger.info("Menu: Choosing default option for difficulty (a)")
            return 'a'
        
        else:
            # Unknown menu - log and return None instead of guessing
            logger.warning(f"Menu: Unknown menu type '{menu_type}', cannot choose")
            return None

    def _display_screen(self, screen: str, action: str = None) -> None:
        """
        Display the current game screen and bot status.
        
        Args:
            screen: Game output to display (with ANSI codes preserved for color)
            action: Current action being performed
        """
        if not screen:
            logger.warning("_display_screen called with empty screen")
            return
        
        try:
            import sys
            
            # Keep ANSI codes for display (colors are important for readability)
            display_screen = screen
            
            # Split into lines but preserve empty lines (needed for dungeon map)
            lines = display_screen.split('\n')
            
            # Clear screen and move to top
            sys.stdout.write("\033[2J\033[H")  # Clear screen and move cursor to top
            sys.stdout.flush()
            
            # Display game screen content with ANSI colors intact
            for line in lines:
                sys.stdout.write(line + '\n')
            
            sys.stdout.flush()
            
            # Log the action
            logger.info(f"Move {self.move_count:04d}: {self.last_action} ({len(display_screen)} bytes)")
        except Exception as e:
            logger.error(f"Display error: {e}", exc_info=True)

    def _display_screen_visual(self, visual_screen: str, action: str = None) -> None:
        """
        Display the FULL accumulated visual screen from pyte buffer.
        
        This shows the complete rendered state of the terminal, not just incremental deltas.
        Perfect for real-time feedback as the bot progresses.
        
        Args:
            visual_screen: The full visual screen from screen_buffer.get_screen_text()
            action: Description of what the bot is doing
        """
        if not visual_screen or not visual_screen.strip():
            return
        
        try:
            import sys
            
            # Clear screen and move to top
            sys.stdout.write("\033[2J\033[H")  # Clear screen and move cursor to top
            sys.stdout.flush()
            
            # Display the complete accumulated game screen
            # This is the full visual state, not just what changed
            sys.stdout.write(visual_screen)
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Error displaying visual screen: {e}")

    def run(self, max_steps: int = 1000) -> None:
        """
        Run the bot.
        
        Args:
            max_steps: Maximum number of actions to take
        """
        self.max_steps = max_steps  # Store for display in TUI
        if not self.local_client.connect():
            logger.error("Failed to connect to server")
            return

        # Mark that we've connected in the state tracker
        self.state_tracker.connect()

        # Display unified TUI from the start, including startup sequence
        self._log_activity("Bot started, connecting to Crawl", "info")

        # Handle startup menus and select Dungeon Crawl
        logger.info("Handling startup menus...")
        if not self._local_startup():
            logger.error("Failed to complete startup sequence")
            self.local_client.disconnect()
            return
        logger.info("Startup complete, game started")
        
        # Mark that gameplay has officially started (we've passed character creation)
        self.gameplay_started = True

        try:
            # Main game loop
            consecutive_no_output = 0
            max_consecutive_no_output = 20  # If 20 reads with no output, consider game paused
            last_display = 0  # Track when we last displayed
            
            # Debug: Read and display initial game state
            logger.info("Reading initial game state...")
            for debug_i in range(3):
                initial_output = self.local_client.read_output(timeout=1.0)
                if initial_output:
                    self.last_screen = initial_output
                    logger.info(f"Got initial output on attempt {debug_i+1}: {len(initial_output)} bytes")
                    break
                else:
                    logger.debug(f"No output on attempt {debug_i+1}")
            
            # Log the initial game state
            if self.last_screen:
                logger.info(f"Displaying game screen with {len(self.last_screen)} bytes")
                self._log_screen_and_action(self.last_screen, "Game Started - Initial State")
                self._save_debug_screen(self.last_screen, "Game Started - Initial State")
                self._display_tui_to_user("Game started, reading state")
                
                # Capture initial experience for tracking
                # At startup, screen buffer may not be initialized yet, so parse raw output
                self.parser.parse_output(self.last_screen)
                self.initial_experience_level = self.parser.state.experience_level
                self.initial_experience_progress = self.parser.state.experience_progress
                logger.info(f"Initial experience: Level {self.initial_experience_level}, Progress {self.initial_experience_progress}%")
            else:
                logger.warning("No game screen received after login!")
            
            while self.move_count < max_steps:
                # Read current state - wait for screen to stabilize before analyzing
                # During gameplay, server typically responds within 1-2 seconds
                # Using shorter timeout (1.5s) to reduce lag while still ensuring stability
                logger.debug(f"Move {self.move_count}: Reading stable output...")
                output = self.local_client.read_output_stable(timeout=1.5, stability_threshold=0.3)
                
                if output:
                    logger.info(f"Move {self.move_count}: Got stable screen with {len(output)} bytes")
                    consecutive_no_output = 0
                    
                    # Update screen buffer with PTY output to build complete visual state
                    self.screen_buffer.update_from_output(output)
                    
                    # Parse game state from the accumulated buffer (not raw delta)
                    # Buffer contains complete reconstructed display with all information
                    buffer_text = self.screen_buffer.get_screen_text()
                    self.last_screen = output  # Keep raw for logging
                    self.parser.parse_output(buffer_text)
                    
                    # Detect and log exploration events from the buffer
                    self._detect_exploration_events(buffer_text)
                    
                    # Check game over conditions using buffer text
                    if self.parser.is_game_over(buffer_text):
                        logger.info("Game over detected")
                        self._log_screen_and_action(self.last_screen, "GAME OVER")
                        self._save_debug_screen(self.last_screen, "GAME OVER")
                        self._display_screen(self.last_screen, "Game Over!")
                        break
                else:
                    logger.debug(f"Move {self.move_count}: No new output from server (using cached screen)")
                    consecutive_no_output += 1
                
                # Decide next action based on current game state
                # Use screen buffer text (clean reconstructed state) for enemy detection
                # Raw last_screen may have jumbled ANSI codes; pyte buffer has accurate reconstruction
                screen_for_decision = self.screen_buffer.get_screen_text() if self.last_screen else ""
                action = self._decide_action(screen_for_decision)
                action_desc = f"Sending '{action}'" if action else "Wait"
                logger.debug(f"Move {self.move_count}: Decided action: {action}")
                
                try:
                    if action:
                        logger.info(f"Move {self.move_count + 1}: Sending '{action}' ({self.action_reason})")
                        self.last_action_sent = action  # Track the action we're sending
                        self.local_client.send_command(action)
                        self.move_count += 1
                        
                        # Wait for server to process the command (local needs more time)
                        logger.debug(f"Waiting 0.25 seconds for server to process '{action}'...")
                        time.sleep(0.25)
                        
                        # Read the response - wait for stable output
                        response = self.local_client.read_output_stable(timeout=3.5, stability_threshold=0.3)
                        if response:
                            consecutive_no_output = 0  # Reset idle counter when we get any output
                            
                            # Use raw response directly for parsing and display
                            self.last_screen = response
                            # Update screen buffer with the new output so visual display shows full state
                            self.screen_buffer.update_from_output(response)
                            self.parser.parse_output(response)
                        else:
                            logger.error(f"No response from server after sending '{action}'")
                            # Detailed diagnostics for debugging
                            logger.error(f"  Last screen size: {len(self.last_screen) if self.last_screen else 0} bytes")
                            logger.error(f"  Health parsed: {self.parser.state.health}/{self.parser.state.max_health}")
                            logger.error(f"  Action chosen: '{action}'")
                            if self.last_screen:
                                clean = self._clean_ansi(self.last_screen)
                                logger.error(f"  Last screen preview: {clean[:100]}...")
                            self.unchanged_screen_count += 1
                        
                        # Check if we've had too many unchanged screens
                        if self.unchanged_screen_count >= self.max_unchanged_screens:
                            logger.error(f"🔴 LOOP DETECTED: Screen unchanged {self.max_unchanged_screens} times in a row")
                            logger.error(f"🔴 Last action: '{action}'")
                            logger.error(f"🔴 Last health: {self.parser.state.health}/{self.parser.state.max_health}")
                            logger.error(f"🔴 Server not responding properly - exiting gameplay loop")
                            if self.last_screen:
                                clean = self._clean_ansi(self.last_screen)
                                logger.error(f"🔴 Last screen: {clean[:150]}...")
                            break
                        
                        # Log action to activity panel
                        if self.action_reason:
                            self._log_activity(f"Move {self.move_count}: {self.action_reason}", "info")
                        
                        # Log screen and action
                        if self.last_screen:
                            self._log_screen_and_action(self.last_screen, f"Sending '{action}'")
                            self._save_debug_screen(self.last_screen, f"Move {self.move_count}: Sending '{action}'")
                        
                        # Display every move for real-time feedback - show full screen state
                        self._display_tui_to_user(self.action_reason or f"Sending '{action}'")
                    else:
                        # Default to wait command (dot)
                        logger.info(f"No explicit action decided, sending wait '.'")
                        
                        # Log action to activity panel
                        self._log_activity(f"Move {self.move_count}: Waiting (no action decided)", "debug")
                        
                        self.local_client.send_command('.')
                        self.move_count += 1
                        
                        # Wait for server to process (at least 2 seconds)
                        logger.debug("Waiting 3 seconds for server to process '.'...")
                        time.sleep(3.0)
                        
                        # Read the response with longer timeout
                        response = self.local_client.read_output(timeout=3.0)
                        if response:
                            # Clean both screens for comparison
                            prev_clean = self._clean_ansi(self.last_screen) if self.last_screen else ""
                            curr_clean = self._clean_ansi(response)
                            
                            # Check if screen actually changed
                            if curr_clean == prev_clean:
                                self.unchanged_screen_count += 1
                                logger.warning(f"Screen unchanged after '.' ({self.unchanged_screen_count}/{self.max_unchanged_screens})")
                            else:
                                self.unchanged_screen_count = 0  # Reset counter on change
                                logger.info(f"Screen CHANGED: {len(self.last_screen) if self.last_screen else 0} → {len(response)} bytes")
                                
                            self.last_screen = response
                            self.parser.parse_output(response)
                        else:
                            logger.error("No response from server after sending '.'")
                            # Detailed diagnostics for debugging
                            logger.error(f"  Last screen size: {len(self.last_screen) if self.last_screen else 0} bytes")
                            logger.error(f"  Health parsed: {self.parser.state.health}/{self.parser.state.max_health}")
                            if self.last_screen:
                                has_health = 'Health:' in self.last_screen or 'health:' in self.last_screen
                                has_time = 'Time:' in self.last_screen
                                has_combat = any(indicator in self.last_screen for indicator in [
                                    'You encounter', 'block', 'miss', 'hits', 'damage', 'rat', 'bat'
                                ])
                                logger.error(f"  Gameplay indicators - Health:{has_health}, Time:{has_time}, Combat:{has_combat}")
                                clean = self._clean_ansi(self.last_screen)
                                logger.error(f"  Last screen preview: {clean[:100]}...")
                            self.unchanged_screen_count += 1
                        
                        # Check if we've had too many unchanged screens
                        if self.unchanged_screen_count >= self.max_unchanged_screens:
                            logger.error(f"🔴 LOOP DETECTED: Screen unchanged {self.max_unchanged_screens} times in a row")
                            logger.error(f"🔴 Last command: '.' (wait)")
                            logger.error(f"🔴 Last health: {self.parser.state.health}/{self.parser.state.max_health}")
                            logger.error(f"🔴 Server not responding properly - exiting gameplay loop")
                            if self.last_screen:
                                clean = self._clean_ansi(self.last_screen)
                                logger.error(f"🔴 Last screen: {clean[:150]}...")
                            break
                        
                        # Log screen and action
                        if self.last_screen:
                            self._log_screen_and_action(self.last_screen, "Waiting/Resting (.)")
                            self._save_debug_screen(self.last_screen, f"Move {self.move_count}: Waiting/Resting (.)")
                        
                        # Display every move for real-time feedback - show full screen state
                        self._display_tui_to_user("Waiting/Resting (.)")
                except (OSError, Exception) as e:
                    logger.error(f"Connection error: {e}")
                    break
                
                # Break if too many reads without output (might indicate disconnection)
                if consecutive_no_output > max_consecutive_no_output:
                    logger.warning(f"No output for {consecutive_no_output} reads, ending game")
                    if self.last_screen:
                        self._save_debug_screen(self.last_screen, "Connection idle, ending")
                        self._display_tui_to_user("Connection idle, ending")
                    break

            # Gracefully quit the game
            logger.info(f"Bot finished after {self.move_count} moves")
            self._quit_game_gracefully()
            
            print("\n" + "=" * 80)
            print("GAME SESSION ENDED")
            print("=" * 80)
            self._print_final_stats()

        except KeyboardInterrupt:
            logger.info("Bot interrupted by user")
            # Try to quit gracefully if interrupted
            try:
                self._quit_game_gracefully()
            except:
                pass
        finally:
            # Reset terminal to normal state before disconnecting
            self._reset_terminal()
            self.local_client.disconnect()

    def _detect_items_on_ground(self, output: str) -> bool:
        """
        Detect if there are items on the ground that can be picked up.
        
        Important: We skip items that are not useful:
        - Corpses (carrion) - not useful for combat
        - Missiles (arrows, stones) - not our priority
        
        When using auto-explore (o command), items are automatically picked up.
        Therefore, we should avoid repeatedly trying to grab items if:
        1. We just tried to grab and found nothing ("Nothing to pick up" or "There are no items here")
        2. We're currently in auto-explore mode
        3. Items are corpses/carrion only
        
        Only attempt grab if:
        - Enough moves have passed since last failed grab attempt (5+ moves)
        - Message indicates useful items on ground (excluding corpses/missiles)
        - We don't see "There are no items here" which indicates nothing is actually present
        
        Args:
            output: Current game output
            
        Returns:
            True if useful items are on the ground and we should attempt grab, False otherwise
        """
        if not output:
            return False
        
        clean_output = self._clean_ansi(output) if output else ""
        
        # Check if game says "There are no items here" or "Nothing to pick up"
        # These indicate the grab attempt just failed (or there was nothing on the ground)
        if 'there are no items here' in clean_output.lower() or 'nothing to pick up' in clean_output.lower():
            self.last_grab_attempt = self.move_count
            self.last_grab_failed = True
            logger.debug("Nothing on ground or grab failed - auto-explore likely already picked up items")
            return False
        
        # Check if we recently tried to grab and found nothing
        # If so, don't try again immediately - wait 5+ moves before retrying
        if self.last_grab_failed and (self.move_count < self.last_grab_attempt + 5):
            logger.debug(f"Skipping grab attempt (last grab failed {self.move_count - self.last_grab_attempt} moves ago)")
            return False
        
        # Reset failed flag if we haven't tried to grab in a while (5+ moves)
        if self.last_grab_failed and self.move_count >= self.last_grab_attempt + 5:
            self.last_grab_failed = False
        
        # Check for common item messages indicating items on ground
        # Use message log area from TUI parser for more reliable detection
        screen_text = self.screen_buffer.get_screen_text() if self.last_screen else ""
        if screen_text:
            try:
                tui_parser = DCSSLayoutParser()
                tui_areas = tui_parser.parse_layout(screen_text)
                message_log_area = tui_areas.get('message_log', None)
                if message_log_area:
                    message_content = message_log_area.get_text()
                    
                    # If we see "there are no items here", no point trying to grab
                    if 'there are no items here' in message_content.lower():
                        self.last_grab_failed = True
                        self.last_grab_attempt = self.move_count
                        return False
                    
                    # Check for "You see here" messages
                    if 'you see here' in message_content.lower():
                        # But filter out corpses and unwanted items
                        # Check if the item is a corpse (carrion) - skip these
                        if 'corpse' in message_content.lower():
                            logger.debug("Skipping corpse on ground (not useful)")
                            return False
                        
                        # Filter out missiles (arrows, stones, etc)
                        missile_keywords = ['stone', 'arrow', 'bolt', 'dart', 'javelin', 'sling bullet']
                        if any(keyword in message_content.lower() for keyword in missile_keywords):
                            logger.debug("Skipping missiles on ground (not our priority)")
                            return False
                        
                        # Only return True for useful items
                        return True
            except Exception as e:
                logger.debug(f"Error parsing TUI for items: {e}")
        
        # Fallback: check common item keywords
        # Skip corpses and missiles in fallback
        has_corpse = 'corpse' in clean_output.lower()
        has_missile = any(word in clean_output.lower() for word in ['stone', 'arrow', 'bolt', 'dart', 'javelin', 'sling bullet'])
        
        if has_corpse or has_missile:
            logger.debug("Skipping corpse or missiles detected in output")
            return False
        
        # Only trigger on specific indicators
        has_item_indicator = 'you see here' in clean_output.lower()
        
        return has_item_indicator
    
    def _grab_items(self) -> Optional[str]:
        """
        Send grab command to pick up items from the ground.
        
        Note: When in auto-explore mode (o command), the game automatically picks up items.
        Therefore, if grab fails with "Nothing to pick up", we wait before retrying
        to avoid spamming 'g' commands when auto-explore has already handled item pickup.
        
        Returns:
            Action command to send (usually 'g' for grab)
        """
        # Mark this grab attempt
        self.last_grab_attempt = self.move_count
        self.last_grab_failed = False  # Reset - we're about to try
        
        logger.info("📦 Grabbing items from the ground")
        return self._return_action('g', "Grabbing items from the ground")
    
    def _is_item_pickup_menu(self, output: str) -> bool:
        """
        Detect if we're in the item selection menu that appears after pressing 'g'.
        
        The menu shows "Pick up what? X/Y slots" and lists items by category:
        - Hand Weapons (e.g., "+0 dagger")
        - Missiles (e.g., "5 stones")  
        - Armour (e.g., "leather armour")
        - Carrion (corpses - should skip)
        - etc.
        
        The menu format has item letters (a, b, c, etc) that can be toggled.
        
        Args:
            output: Current game output
            
        Returns:
            True if in item pickup menu, False otherwise
        """
        if not output:
            return False
        
        clean_output = self._clean_ansi(output) if output else ""
        
        # Check for the distinctive "Pick up what?" prompt
        return 'pick up what?' in clean_output.lower()
    
    def _handle_item_pickup_menu(self, output: str) -> Optional[str]:
        """
        Handle the item selection menu that appears after pressing 'g'.
        
        Strategy: We want to skip items that are not useful:
        - Carrion (corpses) - completely skip
        - Missiles (arrows, stones) - not useful for fighter  
        - +0 weapons - we have an axe already
        - Armor with no AC benefit - skip
        
        Since parsing the exact armor AC benefits is complex, we'll use a simple strategy:
        Close the menu with Escape and let auto-explore handle items naturally.
        This prevents us from getting stuck in the menu.
        
        Args:
            output: Current game output (should be item pickup menu)
            
        Returns:
            Action command to handle the menu
        """
        clean_output = self._clean_ansi(output) if output else ""
        
        # Check what categories of items are available
        has_carrion = 'carrion' in clean_output.lower()
        has_missiles = 'missiles' in clean_output.lower()
        has_hand_weapons = 'hand weapons' in clean_output.lower()
        has_armor = 'armour' in clean_output.lower() or 'armor' in clean_output.lower()
        
        logger.debug(f"Item menu: Carrion={has_carrion}, Missiles={has_missiles}, Weapons={has_hand_weapons}, Armor={has_armor}")
        
        # Parse the lines to see what items are available
        lines = clean_output.split('\n')
        has_useful_items = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Skip carrion - completely useless
            if 'kobold corpse' in line_lower or 'orc corpse' in line_lower or 'corpse' in line_lower and 'carrion' in clean_output:
                continue
            
            # Skip missiles (arrows, stones, etc)
            if 'stones' in line_lower or 'arrow' in line_lower or 'bolt' in line_lower:
                continue
            
            # Skip +0 weapons (we have an axe already that's as good)
            if '+0' in line_lower and ('dagger' in line_lower or 'sword' in line_lower or 'axe' in line_lower or 'spear' in line_lower):
                continue
            
            # TODO: Could add +1 or +2 weapon detection, but for now skip all non-trivial evaluations
            
        # Since we don't have a good way to evaluate items without deeper parsing,
        # and the items shown are all ones we don't want (corpses, missiles, +0 weapons),
        # close the menu with Escape
        logger.info("📋 Item pickup menu has no useful items - closing with Escape")
        self.in_item_pickup_menu = False
        return self._return_action('\x1b', "Closing item menu (no useful items)")
    
    def _identify_untested_potions(self) -> Optional[str]:
        """
        Check if we have untested potions and quaff one to identify it.
        
        When we encounter a potion with unknown effect, we quaff it to discover the effect.
        This creates a mapping: color -> effect for the current game session.
        
        Returns:
            Action command to quaff a potion, or None if no untested potions
        """
        # Check if we have any untested potions
        untested = self.parser.state.untested_potions
        
        if not untested:
            return None
        
        # Pick the first untested potion
        slot = next(iter(untested))
        color = untested[slot]
        
        logger.info(f"🔮 Found untested {color} potion in slot '{slot}' - quaffing to identify...")
        self._log_activity(f"Quaffing {color} potion (slot {slot}) to identify effect", "info")
        
        # Send quaff command: 'q' + slot letter
        # We need to send this as two separate commands
        self.quaff_slot = slot  # Store for next step
        return self._return_action('q', f"Quaffing {color} potion to identify (slot {slot})")
    
    def _refresh_inventory(self) -> Optional[str]:
        """
        Send command to view inventory ('i' command) and parse the result on next turn.
        
        Returns:
            Action command to open inventory
        """
        # Mark that we're about to enter inventory screen so we can detect it on next turn
        self.in_inventory_screen = True
        self.last_inventory_refresh = self.move_count
        logger.info("📋 Opening inventory screen")
        # Open inventory with 'i' command
        # The inventory screen will be parsed on the next iteration
        return self._return_action('i', "Refreshing inventory display")
    
    def _check_and_handle_inventory_state(self, output: str) -> Optional[str]:
        """
        Check if we're currently in the inventory screen and need to handle input.
        
        When 'i' command is sent, DCSS shows the inventory screen.
        We need to parse it and then exit the screen.
        
        The inventory screen has:
        - Lines with format like "a - item name" or "a) item name"
        - Usually starts with letter(s) and dash/parenthesis
        - May have inventory header showing slots (e.g., "Inventory: 6/52 slots")
        
        Args:
            output: Current game output
            
        Returns:
            Action to take (usually Escape to exit inventory), or None
        """
        clean_output = self._clean_ansi(output) if output else ""
        
        # Check for multiple inventory indicators
        # 1. Look for inventory entries (letter, space/paren, item name)
        inventory_pattern = r'^[a-z]\s*[-\)]\s+'
        in_inventory = any(re.match(inventory_pattern, line.strip()) for line in clean_output.split('\n'))
        
        # 2. Alternative: Look for distinctive inventory header lines like "Inventory: X/Y slots"
        if not in_inventory:
            in_inventory = 'inventory:' in clean_output.lower() and ('slots' in clean_output.lower() or '/' in clean_output)
        
        # 3. If we were expecting inventory and got item entries, that's inventory
        if not in_inventory and self.in_inventory_screen:
            # We sent 'i' command but don't see clear inventory markers
            # Check if screen shows items (this could be inventory or game screen with items visible)
            # Look for consistent item patterns
            lines = clean_output.split('\n')
            item_lines = [line for line in lines if re.match(inventory_pattern, line.strip())]
            if len(item_lines) >= 2:  # At least 2 items visible suggests inventory screen
                in_inventory = True
                logger.debug(f"Detected inventory screen by item count ({len(item_lines)} items)")
        
        if in_inventory:
            logger.debug("Currently in inventory screen")
            # Mark that we're now in inventory screen if we weren't before
            # This catches cases where inventory appears unexpectedly
            if not self.in_inventory_screen:
                logger.info("⚠️ Detected inventory screen without prior 'i' command - handling anyway")
                self.in_inventory_screen = True
            
            # Parse the inventory
            self.parser.parse_inventory_screen(output)
            logger.info(f"📦 Parsed inventory: {len(self.parser.state.inventory_items)} items")
            
            # Log current inventory
            for slot, item in self.parser.state.inventory_items.items():
                logger.debug(f"  {slot}: {item.name} (type={item.item_type}, identified={item.identified})")
            
            # Exit inventory screen with Escape
            return self._return_action('\x1b', "Exiting inventory screen")
        
        return None
    
    def _parse_potion_effect_from_message(self, output: str) -> Optional[Tuple[str, str]]:
        """
        Parse the effect of a recently quaffed potion from message log.
        
        After quaffing an untested potion, DCSS displays messages about the effect:
        "You feel invigorated." -> healing
        "You glow briefly." -> resistance
        etc.
        
        Args:
            output: Game output containing messages
            
        Returns:
            Tuple of (color, effect) if we can determine it, None otherwise
        """
        clean_output = self._clean_ansi(output) if output else ""
        
        # Common potion effect messages
        potion_effects = {
            'healing': ['you feel much better', 'you are healed', 'wounds are healed', 'recover'],
            'cure poison': ['poison is cured', 'lose the poison', 'no longer poisoned'],
            'might': ['you feel strong', 'you feel invigorated', 'feel mighty'],
            'magic': ['glow briefly', 'feel more magical', 'magic improves'],
            'agility': ['feel quick', 'feel nimble', 'faster'],
            'resistance': ['feel resistant', 'protected from elements', 'more resilient'],
            'levitation': ['you float', 'you ascend', 'lose your footing'],
            'flight': ['you fly', 'grow wings', 'soar'],
        }
        
        # Try to match effect from messages
        for effect, keywords in potion_effects.items():
            for keyword in keywords:
                if keyword in clean_output.lower():
                    # Get the color from our untested potions tracking
                    # For now, just return the effect (color will be matched by caller)
                    return ('unknown_color', effect)
        
        return None
    
    def _find_and_equip_better_armor(self) -> Optional[str]:
        """
        Detect better armor/clothing/rings and equip them to improve AC.
        
        Scans inventory for armor items with better AC than currently equipped.
        Sends 'e' command to equip when found.
        
        Returns:
            Action command to equip better armor, or None if no improvement found
        """
        # Find better armor
        better_armor = self.parser.find_better_armor()
        
        if not better_armor:
            return None
        
        slot, item = better_armor
        
        # Only equip if significant improvement or currently unequipped slot
        if item.ac_value < -2:  # At least +2 protection
            logger.info(f"🛡️ Found better armor: {item.name} (AC {item.ac_value}) in slot '{slot}'")
            self.equip_slot = slot  # Store for next step
            return self._return_action('e', f"Equipping better armor: {item.name}")
        
        return None
    
    def _mark_equipped_items(self, output: str) -> None:
        """
        Mark items as equipped based on inventory screen.
        
        In DCSS inventory screen, equipped items are usually marked with a '*' or similar.
        This method detects and marks them.
        
        Args:
            output: Inventory screen output
        """
        # Look for equipped item markers (format might be: "a*" or "[a]" or similar)
        # For now, we'll look for items that appear in the status line
        clean = self._clean_ansi(output) if output else ""
        
        # This is a placeholder - actual implementation would parse inventory screen
        # to detect which items are marked as equipped
        # For DCSS, we'd look at the inventory display to see marked items
        pass

    def _reset_terminal(self) -> None:
        """Reset terminal to normal state (clear ANSI codes, reset colors, show cursor)."""
        try:
            import sys
            # Reset all attributes
            sys.stdout.write('\033[0m')      # Reset attributes
            sys.stdout.write('\033[?25h')    # Show cursor
            sys.stdout.write('\033[H')       # Move to home
            sys.stdout.write('\033[2J')      # Clear screen
            sys.stdout.flush()
        except:
            pass

    def _quit_game_gracefully(self) -> None:
        """
        Gracefully quit the game using Ctrl-Q, handle confirmation,
        and capture end-of-game screens to log.
        """
        try:
            logger.info("=" * 80)
            logger.info("INITIATING GRACEFUL GAME EXIT")
            logger.info("=" * 80)
            
            # First, get character experience/progression info before quitting
            logger.info("Retrieving character experience info with 'E' command...")
            self.local_client.send_command('E')
            time.sleep(2.0)  # Wait for response
            
            # Read experience screen
            exp_output = self.local_client.read_output(timeout=2.0)
            if exp_output:
                self.last_screen = exp_output
                logger.info("Character experience screen received")
                self._log_screen_and_action(exp_output, "CHARACTER EXPERIENCE - Final Stats")
                self._display_screen(exp_output, "Final Character Experience Stats")
                
                # Capture final state from the experience screen (still has valid health/mana)
                self.parser.parse_output(exp_output)
                self.final_health = self.parser.state.health
                self.final_max_health = self.parser.state.max_health
                self.final_mana = self.parser.state.mana
                self.final_max_mana = self.parser.state.max_mana
                self.final_gold = self.parser.state.gold
                self.final_location = f"{self.parser.state.dungeon_branch}:{self.parser.state.dungeon_level}"
                logger.info(f"Captured final state - HP: {self.final_health}/{self.final_max_health}, Mana: {self.final_mana}/{self.final_max_mana}, Gold: {self.final_gold}")
                
                time.sleep(0.25)  # Let user see the stats
            else:
                logger.warning("No response to 'E' command")
            
            # Now send Ctrl-Q to quit
            logger.info("Sending Ctrl-Q to quit game...")
            self.local_client.send_command('\x11')  # Ctrl-Q
            time.sleep(0.5)
            
            # Read confirmation prompt
            output = self.local_client.read_output(timeout=2.0)
            if output:
                self.last_screen = output
                clean = self._clean_ansi(output).lower()
                logger.info(f"Received quit prompt: {repr(clean[:300])}")
                self._log_screen_and_action(output, "QUIT PROMPT")
                
                # Check for "quit" confirmation request (must type the word "quit")
                if 'quit' in clean or 'abandon' in clean or 'really' in clean:
                    # Check if it's asking to type "quit"
                    if 'type quit' in clean or 'enter quit' in clean or 'type the word' in clean:
                        logger.info("Server asking to type 'quit' to confirm... sending 'quit'")
                        self.local_client.send_command('quit')
                        time.sleep(0.5)
                        self.local_client.send_command('\r')  # Send enter/return
                        time.sleep(1.0)
                    else:
                        # Generic confirmation prompt
                        logger.info("Confirming character abandon with 'y'...")
                        self.local_client.send_command('y')
                        time.sleep(1.0)
                    
                    # Capture end-of-game screens
                    logger.info("Capturing end-of-game state screens...")
                    for screen_num in range(5):  # Try to capture up to 5 screens
                        end_output = self.local_client.read_output(timeout=1.5)
                        if end_output:
                            self.last_screen = end_output
                            clean_end = self._clean_ansi(end_output).lower()
                            logger.info(f"End-game screen {screen_num + 1}: {len(end_output)} bytes")
                            self._log_screen_and_action(end_output, f"CHARACTER ABANDONED - Screen {screen_num + 1}")
                            self._display_screen(end_output, f"End-game screen {screen_num + 1}")
                            
                            # Stop if we see character selection or main menu
                            if any(word in clean_end for word in ['character', 'select', 'welcome to', 'not logged in']):
                                logger.info("Reached character selection or main menu")
                                break
                            
                            time.sleep(0.3)
                        else:
                            logger.debug(f"No more output for screen {screen_num + 1}")
                            break
                    
                    logger.info("✓ Game exited gracefully")
                else:
                    logger.info("No clear quit confirmation detected, sending 'quit' anyway...")
                    self.local_client.send_command('quit')
                    time.sleep(0.5)
                    self.local_client.send_command('\r')  # Send enter
                    time.sleep(1.0)
            else:
                logger.warning("No response to Ctrl-Q, attempting to send 'quit' anyway")
                self.local_client.send_command('quit')
                time.sleep(0.5)
                self.local_client.send_command('\r')
                time.sleep(1.0)
                
        except Exception as e:
            logger.error(f"Error during graceful quit: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _return_action(self, action: str, reason: str) -> str:
        """
        Helper method to return an action while setting the reason.
        
        Args:
            action: The action command to send
            reason: The reason for this action
            
        Returns:
            The action command
        """
        self.action_reason = reason
        return action
    
    def _prepare_decision_context(self, output: str) -> DecisionContext:
        """
        Prepare game state context for DecisionEngine evaluation.
        
        This method extracts all relevant game state into a DecisionContext object
        that the DecisionEngine uses to make decisions via rule evaluation.
        
        Args:
            output: Current screen text (from pyte buffer via get_screen_text())
            
        Returns:
            DecisionContext with all current game state
        """
        # Parse output to extract state
        self.parser.parse_output(output)
        
        # Get current values from parser
        health = self.parser.state.health
        max_health = self.parser.state.max_health
        level = self.parser.state.experience_level
        dungeon_level = self.parser.state.dungeon_level
        
        # Detect game situations (using existing helper methods)
        enemy_detected, enemy_name = self._detect_enemy_in_range(output)
        enemy_direction = None
        if enemy_detected:
            # Calculate direction to move toward the enemy when low health
            enemy_direction = self._calculate_direction_to_enemy(output, enemy_name)
        
        items_on_ground = self._detect_items_on_ground(output)
        in_shop = self._is_in_shop(output)
        in_inventory_screen = self._check_and_handle_inventory_state(output) is not None
        in_item_pickup_menu = self._is_item_pickup_menu(output)
        in_menu = self.state_tracker.in_menu_state()
        
        # Check for various prompts
        has_more_prompt = '--more--' in output
        attribute_increase_prompt = ('Increase (S)trength' in output or 
                                     'Increase (S)trength, (I)ntelligence, or (D)exterity' in output)
        save_game_prompt = 'save game and return to main menu' in output.lower()
        has_level_up = self.parser.has_level_up_message(output)
        
        # Check gameplay indicators
        has_gameplay_indicators = (health > 0 or self.last_known_health > 0) and level > 0
        
        # Create and return context
        return DecisionContext(
            output=output,
            health=health,
            max_health=max_health,
            level=level,
            dungeon_level=dungeon_level,
            enemy_detected=enemy_detected,
            enemy_name=enemy_name,
            enemy_direction=enemy_direction,
            items_on_ground=items_on_ground,
            in_shop=in_shop,
            in_inventory_screen=in_inventory_screen,
            in_item_pickup_menu=in_item_pickup_menu,
            in_menu=in_menu,
            equip_slot_pending=self.equip_slot is not None,
            quaff_slot_pending=self.quaff_slot is not None,
            has_level_up=has_level_up,
            has_more_prompt=has_more_prompt,
            attribute_increase_prompt=attribute_increase_prompt,
            save_game_prompt=save_game_prompt,
            last_action_sent=self.last_action_sent,
            last_level_up_processed=self.last_level_up_processed,
            last_attribute_increase_level=self.last_attribute_increase_level,
            last_equipment_check=self.last_equipment_check,
            last_inventory_refresh=self.last_inventory_refresh,
            move_count=self.move_count,
            has_gameplay_indicators=has_gameplay_indicators,
            gameplay_started=self.gameplay_started,
            goto_state=self.goto_state,
            goto_target_level=self.goto_target_level
        )
        return action

    def _decide_action(self, output: str) -> Optional[str]:
        """
        Decide what action to take based on game state using DecisionEngine.
        
        Evaluates all configured rules in priority order and returns the first matching
        rule's action.
        
        Args:
            output: Current game state from screen buffer
            
        Returns:
            Command string to send to game, or None if no rules match
        """
        try:
            # Prepare complete game state context for engine
            context = self._prepare_decision_context(output)
            
            # Evaluate engine rules (highest priority first)
            command, reason = self.decision_engine.decide(context)
            
            if command is not None:
                self.engine_decisions_made += 1
                return self._return_action(command, reason)
            
            # Engine returned None - this should not happen with default engine
            # but provide a safe fallback
            logger.warning("No decision rule matched - returning explore")
            self.engine_decisions_made += 1
            return self._return_action('o', "Auto-explore (no rule matched)")
            
        except Exception as e:
            logger.error(f"Error in DecisionEngine: {e}")
            logger.debug(f"Traceback: {e.__traceback__}")
            # Safe fallback: explore
            return self._return_action('o', "Auto-explore (engine error fallback)")
    
    
    def _local_startup(self) -> bool:
        """
        Handle startup sequence for local Crawl execution.
        
        Uses state machine to detect startup/menu screens and send appropriate inputs.
        Handles name entry, menu selection, and character confirmation.
        
        PTY Configuration: The PTY is run in COOKED MODE (canonical + echo enabled).
        This is required for Crawl's interactive menu system to work correctly.
        Cooked mode provides line-buffered input which allows Crawl to process
        complete menu selections properly.
        
        IMPORTANT: We navigate menus through interactive input ONLY.
        We do NOT use command-line options (like -name, -species, -background) to bypass
        the character creation menus. All menu navigation must be handled by detecting
        menu screens and sending appropriate interactive inputs (letters, arrow keys, Enter).
        This ensures the bot properly demonstrates the full game startup flow.
        
        Returns:
            True if successfully started game, False otherwise
        """
        try:
            logger.info("Waiting for Crawl startup...")
            self._log_activity("Waiting for Crawl startup screen", "info")
            time.sleep(4.0)
            
            # Read initial menu
            output = self.local_client.read_output(timeout=3.0)
            if not output:
                logger.error("No startup menu received!")
                self._log_activity("No startup menu received!", "error")
                return False
            
            self.last_screen = output
            self.screen_buffer.update_from_output(output)
            self._save_debug_screen(output, "STARTUP: Initial menu")
            # Display the TUI immediately when we get the first screen
            self._display_tui_to_user("🎮 Initial Startup Screen")
            self._log_activity("Startup menu detected", "success")
            clean = self._clean_ansi(output)
            logger.info(f"Got {len(output)} bytes from Crawl")
            
            # Use state machine to handle startup sequence
            startup_state_machine = self.char_creation_state
            startup_state_machine.reset()
            
            # Phase 1: Handle name entry and character creation menus
            # In raw mode PTY (which Crawl needs), we send individual keypresses.
            # After entering the name, the game automatically:
            # 1. Selects "Dungeon Crawl" as the default game type (we do NOT manually select it)
            # 2. Proceeds to character creation menus (race, class, background, etc.)
            max_startup_attempts = 50
            name_sent = False
            last_menu_state = None
            
            for attempt in range(max_startup_attempts):
                # On first iteration, use the initial output we already read
                # On subsequent iterations, read new output
                if attempt > 0:
                    logger.debug(f"Attempt {attempt + 1}: Reading output with 2.0s timeout...")
                    output = self.local_client.read_output(timeout=2.0)
                    clean = self._clean_ansi(output) if output else ""
                    if output:
                        self.last_screen = output
                        self.screen_buffer.update_from_output(output)
                        # Display TUI for every screen during startup
                        self._display_tui_to_user(f"Startup phase {attempt + 1}")
                else:
                    logger.debug(f"Attempt {attempt + 1}: Processing initial output ({len(clean)} chars)")
                
                if output:
                    logger.debug(f"Attempt {attempt + 1}: Got {len(output)} bytes")
                else:
                    logger.debug(f"Attempt {attempt + 1}: No output (timeout)")
                
                # Only process if we have output
                if output:
                    has_name_prompt = 'enter your name:' in clean.lower()
                    logger.debug(f"Startup phase {attempt + 1}: has_name_prompt={has_name_prompt}, name_sent={name_sent}")
                    logger.debug(f"Output preview (first 200 chars): {clean[:200]}")
                    
                    # Phase 1a: Name entry - send name characters one by one, then Enter
                    if not name_sent and has_name_prompt:
                        logger.debug(f"Startup phase {attempt + 1}: MATCHED - name prompt")
                        name = self._generate_random_name()
                        logger.info(f"Sending character name: {name}")
                        self._log_activity(f"Sending character name: {name}", "info")
                        
                        # First, clear any pre-populated name from previous session using Ctrl+U (clear line)
                        # This deletes from cursor to start of line
                        self.local_client.send_command('\x15')  # Ctrl+U
                        time.sleep(0.1)
                        
                        # Send name as individual keypresses in cbreak mode
                        for char in name:
                            self.local_client.send_command(char)
                            time.sleep(0.05)  # Small delay between characters
                        # Send Enter (\r\n for compatibility)
                        self.local_client.send_command('\r\n')
                        name_sent = True
                        logger.debug(f"Name sent: {name}, sleeping 1.5s for character creation menu to appear...")
                        time.sleep(1.5)
                        continue  # Go to next iteration to read the response
                    
                    # After name submitted, handle character creation menus
                    if name_sent:
                        # Check if we've reached gameplay
                        if 'Time:' in clean and len(clean) > 400:
                            logger.info(f"✓ GAMEPLAY REACHED during startup on attempt {attempt + 1}!")
                            self._log_activity("Gameplay started!", "success")
                            self.last_screen = output
                            self.screen_buffer.update_from_output(output)
                            self.parser.parse_output(output)  # Parse the screen to get correct health values
                            self._display_tui_to_user("🎮 GAMEPLAY STARTED!")
                            return True
                        
                        current_state = startup_state_machine.update(clean.lower())
                        logger.debug(f"Startup phase {attempt + 1}: CharCreation state = {current_state}")
                        logger.debug(f"Output preview (first 150 chars): {clean[:150]}")
                        
                        # If we've transitioned to a new menu state (race, class, background, etc.)
                        if current_state != 'startup' and current_state != 'error' and current_state != last_menu_state:
                            # Save screenshot of the current menu before making a selection
                            menu_screenshots = {
                                'race': 'CHARACTER CREATION: Species Selection',
                                'class_select': 'CHARACTER CREATION: Class Selection',
                                'background': 'CHARACTER CREATION: Background Selection',
                                'skills': 'CHARACTER CREATION: Skills/Equipment Selection',
                            }
                            screenshot_label = menu_screenshots.get(current_state, f'CHARACTER CREATION: {current_state}')
                            self._save_debug_screen(output, screenshot_label)
                            
                            # Determine which key to send based on the menu type
                            selection_map = {
                                'species': ('j', 'Human'),           # j = Human
                                'class_select': ('a', 'Fighter'),  # a = Fighter (for background)
                                'background': ('a', 'Fighter'),    # a = Fighter
                                'skills': ('c', 'War Axe'),        # c = War Axe (weapon selection)
                            }
                            
                            # Get the selection for this menu, default to 'a' if not found
                            selection_key, selection_name = selection_map.get(current_state, ('a', 'first option'))
                            
                            logger.info(f"✓ Detected {current_state} menu - sending '{selection_key}' to select {selection_name}")
                            self._log_activity(f"Selecting {current_state}: '{selection_key}' ({selection_name})", "info")
                            self._display_tui_to_user(f"🎮 {current_state} menu - selecting {selection_name} ({selection_key})")
                            # Send the selection key
                            self.local_client.send_command(selection_key)
                            last_menu_state = current_state
                            logger.debug(f"Sent '{selection_key}' command, sleeping 1.5s before reading next screen...")
                            time.sleep(1.5)
                            continue
                        
                        # If still in startup state but got output, keep trying
                        if current_state == 'startup' and len(output) > 0 and attempt < max_startup_attempts - 1:
                            logger.debug(f"Still in startup state, attempt {attempt + 1}/{max_startup_attempts}")
                            continue
                        elif current_state == 'error':
                            logger.warning(f"State machine entered error state, retrying...")
                            time.sleep(1.0)
                            continue
            
            # Phase 2: If we reach here, we've exhausted attempts. Log final status
            logger.error("Failed to reach gameplay within startup sequence")
            self._log_activity("❌ Failed to reach gameplay", "error")
            output = self.local_client.read_output(timeout=2.0)
            
            if output and len(output) > 200:
                clean = self._clean_ansi(output)
                self.last_screen = output
                self.screen_buffer.update_from_output(output)
                # Display TUI with final attempt
                self._display_tui_to_user("Character creation phase - final attempt")
                
                # Last check for gameplay
                if 'Time:' in clean and len(clean) > 400:
                    logger.info(f"✓ GAMEPLAY REACHED on final check!")
                    self._log_activity("Gameplay started!", "success")
                    self.parser.parse_output(output)  # Parse the screen to get correct health values
                    self._display_tui_to_user("🎮 GAMEPLAY STARTED!")
                    return True
            
            logger.error("⚠️ Did not reach gameplay after startup attempts")
            return False
            
        except Exception as e:
            logger.error(f"Error during startup: {e}", exc_info=True)
            return False
    
    def _has_existing_character(self, output: str) -> bool:
        """
        Check if an existing character was loaded instead of showing character creation.
        
        Args:
            output: The output after 'P' command
            
        Returns:
            True if an existing character is loaded, False if we're at character creation
        """
        if not output:
            return False
        
        clean = self._clean_ansi(output)
        clean_lower = clean.lower()
        
        # Check for game interface indicators (character was loaded)
        game_indicators = [
            'welcome back',
            'welcome to',
            'press ? for a list of commands',
            'health:',  # Character stats
            'magic:',
            ' ac:',      # Note the space before AC to avoid 'place'
            ' xp:',
            ' ev:',
            'dungeon:',
            'dungeon level',
            'exp:',
        ]
        
        has_game_interface = any(phrase in clean_lower for phrase in game_indicators)
        
        # Additional check: look for dungeon visualization characters (#, ., +, etc.)
        # This is pretty specific to DCSS
        has_dungeon_chars = any(char in clean for char in ['#', '.', '+', '-', '|'])
        
        # Also check for the player position marker
        has_player_marker = '@' in clean
        
        # Check if this is actually a menu (creation/selection menu)
        is_menu = any(phrase in clean_lower for phrase in [
            'choose a race',
            'choose a class',
            'choose your',
            'enter a character name',
            'choose a background',
            'choose your abilities',
        ])
        
        # If we have game interface or dungeon chars/player marker AND NOT a menu, then character was loaded
        character_loaded = (has_game_interface or (has_dungeon_chars and has_player_marker)) and not is_menu
        
        if character_loaded:
            logger.info("✓ Existing character detected - will play with this character")
        
        return character_loaded

    def _extract_all_enemies_from_tui(self, output: str) -> list[str]:
        """
        Extract all enemies from the TUI monsters section.
        
        The monsters section in a 40x120 DCSS TUI appears starting at:
        - Line 21, character 41 onwards
        - Format: "X   creature_name" where X is the symbol on the map
        - Multiple monsters can be listed, one per line OR multiple on same line with 3+ spaces between
        
        Args:
            output: Current game output
            
        Returns:
            List of enemy names found in the monsters section, empty list if none
        """
        if not output:
            return []
        
        clean = self._clean_ansi(output)
        lines = clean.split('\n')
        
        enemies = []
        seen = set()  # Avoid duplicates
        
        # Parse the monsters section which starts at line 21 (0-indexed: line 20)
        # and continues for available space
        # Handle two formats:
        # 1. Individual creatures: "K   kobold" (symbol, 3+ spaces, name)
        # 2. Multiple same creatures: "KK  2 kobolds" OR "gg  2 goblins" (symbols, spaces, count, name)
        for line in lines:
            # First try to match the "grouped" format: multiple symbols + count + name
            # Pattern: [a-zA-Z]+ (symbols, 2+, upper or lower) + spaces + digits (count) + spaces + name (word chars only)
            grouped_matches = re.finditer(r'([a-zA-Z]{2,})\s+(\d+)\s+(\w+)', line)
            
            for match in grouped_matches:
                symbols = match.group(1)
                count = int(match.group(2))
                creature_name = match.group(3)
                
                # Reject if symbols are common English words (message artifacts, not creatures)
                # e.g., "Found 19 sling" has symbols="Found" (a message), not creatures
                # Also reject common item names that appear in pickup messages like "here 16x arrows"
                # Also reject equipment status messages like "Nothing quivered"
                invalid_symbols = ['Found', 'You', 'The', 'This', 'That', 'Your', 'And', 'Are', 'But', 'Can', 'For', 'Have', 'Here', 'Just', 'Know', 'Like', 'Make', 'More', 'Now', 'Only', 'Out', 'Over', 'Some', 'Such', 'Take', 'Want', 'Way', 'What', 'When', 'Will', 'With', 'Would', 'have', 'here', 'Nothing']
                if symbols in invalid_symbols:
                    continue
                
                # Validate the entry
                # Reject common items that might appear in "item found" messages
                # Also reject common action keywords from equipment/message sections
                item_keywords = ['arrow', 'dart', 'potion', 'scroll', 'ring', 'amulet', 'wand', 'staff', 'weapon', 'armour', 'armor', 'item', 'stone', 'food', 'poisoned', 'cursed', 'blessed', 'quivered']
                if any(item in creature_name.lower() for item in item_keywords):
                    continue
                    
                if (creature_name and
                    creature_name not in ['place', 'noise', 'time', 'ac', 'ev', 'sh', 'xl', 'next', 'magic', 'health', 'str', 'int', 'dex', 'a', 'o', 'b'] and
                    not any(char in creature_name for char in '#.+=~,|-')):
                    
                    # Add the creature once (we'll rely on the name to avoid duplicates)
                    if creature_name not in seen:
                        enemies.append(creature_name)
                        seen.add(creature_name)
                        logger.debug(f"Monsters section (grouped): {symbols} ({count}x) -> {creature_name}")
            
            # Then try the standard format: single symbol + 3+ spaces + name
            # Only process if no grouped matches (avoid double-counting)
            if not list(re.finditer(r'([a-zA-Z]{2,})\s+(\d+)\s+(\w+)', line)):
                standard_matches = re.finditer(r'([a-zA-Z])\s{3,}([\w\s]+?)(?=\s{3,}[a-zA-Z]|\(|[│]|$)', line)
                
                for match in standard_matches:
                    creature_symbol = match.group(1)
                    creature_name = match.group(2).strip()
                    
                    if (creature_name and
                        creature_symbol not in '│─┌┐└┘┼├┤┬┴' and
                        creature_name not in ['place', 'noise', 'time', 'ac', 'ev', 'sh', 'xl', 'next', 'magic', 'health', 'str', 'int', 'dex', 'a', 'o', 'b'] and
                        not any(char in creature_name for char in '#.+=~,|-') and
                        creature_name not in seen):
                        enemies.append(creature_name)
                        seen.add(creature_name)
                        logger.debug(f"Monsters section (standard): {creature_symbol} -> {creature_name}")
        
        return enemies

    def _extract_enemy_name(self, output: str) -> str:
        """
        Extract the name of the detected enemy from the TUI display.
        
        The TUI monsters section is the authoritative source for enemy names.
        Format: "X   creature_name" where X is the symbol on the dungeon map.
        
        This method extracts the actual enemy name as shown in the TUI,
        representing what the player sees on screen right now.
        
        Args:
            output: Current game output (TUI display)
            
        Returns:
            Enemy name if found in TUI, "enemy" as fallback
        """
        if not output:
            return "enemy"
        
        # Extract all enemies from the TUI monsters section
        # The TUI is the source of truth for current game state
        tui_enemies = self._extract_all_enemies_from_tui(output)
        if tui_enemies:
            # Return the first enemy (most recently encountered)
            return tui_enemies[0]
        
        # Should not reach here if called after _detect_enemy_in_range confirms enemy exists
        logger.debug("No enemy name found in TUI monsters section")
        return "enemy"

    def _detect_enemy_in_range(self, output: str) -> tuple[bool, str]:
        """
        Detect if there's an enemy in range using the TUI display as source of truth.
        
        The TUI monsters section is the authoritative source for enemies in view.
        Decision logic is based on what the TUI currently displays, not message streams.
        
        The TUI monsters section format:
            X   creature_name
        Located at line 21, character 41 in the 40x120 display.
        
        Args:
            output: Current game output (TUI display)
            
        Returns:
            Tuple of (detected: bool, enemy_name: str) - e.g., (True, "rat") or (False, "")
        """
        if not output:
            return False, ""
        
        # PRIMARY: Extract enemies from TUI monsters section
        # This is the authoritative source of game state
        enemies = self._extract_all_enemies_from_tui(output)
        
        if enemies:
            # Return the first enemy (most recently encountered or visible)
            enemy_name = enemies[0]
            logger.debug(f"TUI monsters section shows enemy in range: {enemy_name}")
            return True, enemy_name
        
        logger.debug("No enemies shown in TUI monsters section")
        return False, ""

    def _calculate_direction_to_enemy(self, output: str, enemy_name: str) -> Optional[str]:
        """
        Calculate the direction to move toward an enemy.
        
        Uses the TUI monsters list to find the enemy character, then scans the map
        to locate the player (@) and enemy character, calculating the optimal direction.
        
        DCSS movement keys:
        - 'h' = left,  'j' = down,  'k' = up,    'l' = right
        - 'y' = up-left,  'u' = up-right,  'b' = down-left,  'n' = down-right
        
        Args:
            output: Current game output (TUI display)
            enemy_name: Name of the enemy to move toward
            
        Returns:
            A DCSS direction key ('h', 'j', 'k', 'l', 'y', 'u', 'b', 'n') or None if unable to calculate
        """
        if not output or not enemy_name:
            return None
        
        try:
            clean = self._clean_ansi(output)
            lines = clean.split('\n')
            
            # Find the enemy character from the TUI monsters section
            # The monsters section shows: "X   creature_name" where X is the map symbol
            enemy_symbol = None
            for line in lines:
                # Look for the enemy name in the line
                if enemy_name in line:
                    # Extract the first character of the line as the symbol
                    # Pattern: "[a-zA-Z]\s{3,}name" = symbol with 3+ spaces then name
                    match = re.search(r'^([a-zA-Z])\s{3,}' + re.escape(enemy_name), line)
                    if match:
                        enemy_symbol = match.group(1)
                        logger.debug(f"Found enemy symbol '{enemy_symbol}' for {enemy_name}")
                        break
            
            if not enemy_symbol:
                logger.debug(f"Could not find enemy symbol for {enemy_name}")
                return None
            
            # Now find the map section and locate player (@) and enemy
            # The map typically spans lines 1-20 (0-indexed: 1-20), columns 0-80 (typical map width)
            player_row = None
            player_col = None
            enemy_row = None
            enemy_col = None
            
            for row_idx, line in enumerate(lines[:21]):  # Map is typically in first 21 lines
                # Find player (@)
                if '@' in line:
                    player_col = line.index('@')
                    player_row = row_idx
                
                # Find enemy character
                if enemy_symbol in line:
                    # Make sure this is the map, not the monsters section
                    # (monsters section is typically after line 21)
                    if row_idx <= 20:
                        enemy_col = line.index(enemy_symbol)
                        enemy_row = row_idx
            
            if player_row is None or enemy_row is None:
                logger.debug(f"Could not locate player or enemy on map (player: {player_row}, enemy: {enemy_row})")
                return None
            
            # Calculate direction from player to enemy
            row_diff = enemy_row - player_row  # Positive = down, negative = up
            col_diff = enemy_col - player_col  # Positive = right, negative = left
            
            logger.debug(f"Player at ({player_row}, {player_col}), Enemy at ({enemy_row}, {enemy_col}), diff: ({row_diff}, {col_diff})")
            
            # Determine direction based on differences
            # Prioritize horizontal/vertical over diagonal when one difference is much larger
            if abs(row_diff) > abs(col_diff):
                # Vertical dominates
                if row_diff > 0:
                    return 'j'  # down
                else:
                    return 'k'  # up
            elif abs(col_diff) > abs(row_diff):
                # Horizontal dominates
                if col_diff > 0:
                    return 'l'  # right
                else:
                    return 'h'  # left
            else:
                # Diagonal - use appropriate diagonal key
                if row_diff > 0:  # Down
                    if col_diff > 0:
                        return 'n'  # down-right
                    else:
                        return 'b'  # down-left
                else:  # Up
                    if col_diff > 0:
                        return 'u'  # up-right
                    else:
                        return 'y'  # up-left
        
        except Exception as e:
            logger.debug(f"Error calculating direction to enemy: {e}")
            return None

    def _is_in_shop(self, output: str) -> bool:
        """
        Detect if player is currently in a shop interface.
        
        Shop screens have characteristic patterns:
        - "Welcome to [ShopName]'s [ShopType] Shop!" at the top
        - Items listed with format: "a -  360 gold   an amulet..."
        - Status line with "[Esc] exit" command at the bottom
        
        Args:
            output: Current game output
            
        Returns:
            True if in a shop interface, False otherwise
        """
        if not output:
            return False
        
        clean = self._clean_ansi(output)
        
        # Check for characteristic shop patterns
        # Primary check: "Welcome to" + "Shop!" is the most reliable indicator
        has_welcome_line = 'Welcome to' in clean and "Shop!" in clean
        
        # Secondary check: "[Esc] exit" command (present in shop interface)
        has_esc_exit = "[Esc] exit" in clean
        
        # If both patterns present, definitely in a shop
        if has_welcome_line and has_esc_exit:
            logger.info("🏪 Shop interface detected")
            return True
        
        return False

    def _find_direction_to_enemy(self, output: str) -> str:
        """
        Find the direction to move toward the detected enemy.
        
        Uses TUI monsters section to get the enemy symbol, then scans the map to find it.
        This ensures we move toward the correct enemy, not nearby UI elements.
        
        Uses roguelike direction keys:
        - h = left, j = down, k = up, l = right
        - y = up-left, u = up-right, b = down-left, n = down-right
        
        Args:
            output: Current game output containing the visible map
            
        Returns:
            Direction key to move toward enemy, or '.' (wait) if no direction found
        """
        if not output:
            return '.'
        
        # Get the enemy from TUI monsters section (not by scanning for lowercase)
        # This ensures we target the correct enemy, not UI artifacts
        enemies_from_tui = self._extract_all_enemies_from_tui(output)
        if not enemies_from_tui:
            logger.debug("No enemies in TUI monsters section")
            return '.'
        
        # We'll look for the enemy symbol on the map
        # First, we need to get the creature symbol from somewhere
        # The TUI monsters section shows "S   ball python", so we need to parse that
        # Let's scan the output for the "X   name" pattern to get the symbol
        
        enemy_symbol = None
        for line in output.split('\n'):
            # Look for the monster entry format: "S   ball python"
            # Match: single char + 3+ spaces + creature name
            match = re.match(r'^([a-zA-Z])\s{3,}([\w\s]+)', line)
            if match:
                symbol, creature_name = match.groups()
                creature_name_clean = creature_name.strip()
                # Check if this is the enemy we're looking for (first one from TUI)
                if creature_name_clean == enemies_from_tui[0]:
                    enemy_symbol = symbol
                    break
        
        if not enemy_symbol:
            logger.debug(f"Could not find enemy symbol for {enemies_from_tui[0]}")
            return '.'
        
        # Now scan the map for this specific enemy symbol
        lines = output.split('\n')
        player_pos = None
        enemy_pos = None
        
        # Only scan the map area (rows 0-25, columns 0-79)
        for y, line in enumerate(lines):
            if y > 25:  # Map area ends around row 25-26
                break
            for x in range(min(80, len(line))):
                char = line[x]
                if char == '@':
                    player_pos = (x, y)
                elif char == enemy_symbol:
                    enemy_pos = (x, y)
        
        if not player_pos or not enemy_pos:
            logger.debug(f"Could not find player or enemy '{enemy_symbol}' on map (player={player_pos}, enemy={enemy_pos})")
            return '.'
        
        # Calculate direction to enemy
        player_x, player_y = player_pos
        enemy_x, enemy_y = enemy_pos
        
        dx = 0 if enemy_x == player_x else (1 if enemy_x > player_x else -1)
        dy = 0 if enemy_y == player_y else (1 if enemy_y > player_y else -1)
        
        # Map (dx, dy) to direction keys
        direction_map = {
            (-1, -1): 'y',  # up-left
            (0, -1): 'k',   # up
            (1, -1): 'u',   # up-right
            (-1, 0): 'h',   # left
            (0, 0): '.',    # on top (wait)
            (1, 0): 'l',    # right
            (-1, 1): 'b',   # down-left
            (0, 1): 'j',    # down
            (1, 1): 'n',    # down-right
        }
        
        distance = abs(enemy_x - player_x) + abs(enemy_y - player_y)
        direction = direction_map.get((dx, dy), '.')
        
        logger.debug(f"Map scan found enemy '{enemy_symbol}' ({enemies_from_tui[0]}) at ({enemy_x}, {enemy_y}), player at ({player_x}, {player_y}), distance={distance}")
        logger.info(f"🎯 Moving toward {enemy_symbol} {enemies_from_tui[0]} (distance: {distance}, direction: {direction})")
        return self._return_action(direction, f"Moving toward {enemy_symbol}")

    def _print_final_stats(self) -> None:
        """Print final game statistics to both console and log file."""
        state = self.parser.state
        
        # Use captured final state values (from before quitting)
        # Don't use parser.state directly since it gets reset by quit screens
        final_health = self.final_health if self.final_health > 0 else state.health
        final_max_health = self.final_max_health if self.final_max_health > 0 else state.max_health
        final_mana = self.final_mana if self.final_mana > 0 else state.mana
        final_max_mana = self.final_max_mana if self.final_max_mana > 0 else state.max_mana
        final_gold = self.final_gold if self.final_gold > 0 else state.gold
        final_location = self.final_location if self.final_location else f"{state.dungeon_branch}:{state.dungeon_level}"
        
        # Calculate experience delta
        # Experience is tracked as: levels + progress percentage (0-100)
        # So if we go from Level 1, 50% to Level 2, 20%, the delta is 70%
        initial_total = (self.initial_experience_level - 1) * 100 + self.initial_experience_progress
        final_total = (self.final_experience_level - 1) * 100 + self.final_experience_progress
        experience_gained = final_total - initial_total
        
        # Helper function to print and log simultaneously
        def print_and_log(message: str = "") -> None:
            print(message)
            logger.info(message)
        
        print_and_log("=== Final Statistics ===")
        print_and_log(f"Moves: {self.move_count}")
        print_and_log(f"Location: {final_location}")
        print_and_log(f"Health: {final_health}/{final_max_health}")
        print_and_log(f"Mana: {final_mana}/{final_max_mana}")
        print_and_log(f"Experience Level: {state.experience_level} (Progress: {state.experience_progress}%)")
        print_and_log(f"Gold: {final_gold}")
        print_and_log(f"Hunger: {state.hunger_level}")
        print_and_log("")
        print_and_log("=== Experience Gained ===")
        print_and_log(f"Initial: Level {self.initial_experience_level}, {self.initial_experience_progress}% progress")
        print_and_log(f"Final:   Level {self.final_experience_level}, {self.final_experience_progress}% progress")
        print_and_log(f"Total Experience Gained: {experience_gained}% (equivalent to {experience_gained / 100:.2f} levels)")
        
        print_and_log("")
        print_and_log("=== Exploration Summary ===")
        print_and_log(f"Total Moves: {self.move_count}")
        print_and_log(f"Final Gold: {final_gold}")
        print_and_log(f"Items Found: {len(self.items_found)}")
        print_and_log(f"Unique Enemies Encountered: {len(self.enemies_encountered)}")
        print_and_log(f"Total Events: {len(self.exploration_events)}")
        
        # Show unique enemies encountered
        if self.enemies_encountered:
            print_and_log("")
            print_and_log("Enemies Encountered:")
            for enemy in sorted(self.enemies_encountered):
                print_and_log(f"  - {enemy}")
        
        # Show unique items found
        if self.items_found:
            print_and_log("")
            print_and_log("Items Found:")
            for item in self.items_found[:10]:  # Show first 10
                print_and_log(f"  - {item}")
            if len(self.items_found) > 10:
                print_and_log(f"  ... and {len(self.items_found) - 10} more items")
        
        # Show event log (summary)
        if self.exploration_events:
            print_and_log("")
            print_and_log("Event Log (Summary - Key Events):")
            # Group events by type
            event_counts = {}
            for move, event_type, description in self.exploration_events:
                if event_type not in event_counts:
                    event_counts[event_type] = 0
                event_counts[event_type] += 1
            
            for event_type, count in sorted(event_counts.items()):
                print_and_log(f"  - {event_type.title()}: {count} events")
        
        # Ensure all logs are flushed (loguru handles this automatically)

