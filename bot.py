"""Main bot logic for playing Dungeon Crawl Stone Soup."""

import time
import re
from typing import Optional
from datetime import datetime
import os
import pyte
import random
import string
from loguru import logger

from local_client import LocalCrawlClient
from game_state import GameStateParser
from game_state_machine import GameStateMachine
from char_creation_state_machine import CharacterCreationStateMachine
from bot_unified_display import UnifiedBotDisplay
from credentials import CRAWL_COMMAND


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
        self.ssh_client = LocalCrawlClient(crawl_command=crawl_command or '/usr/games/crawl')
        
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
        self.waiting_for_goto_prompt = False
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
        if 'You have reached level' in clean_output:
            level_match = re.search(r'You have reached level (\d+)', clean_output)
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
        if not self.ssh_client.connect():
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
            self.ssh_client.disconnect()
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
                initial_output = self.ssh_client.read_output(timeout=1.0)
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
                logger.debug(f"Move {self.move_count}: Reading stable output...")
                output = self.ssh_client.read_output_stable(timeout=3.5, stability_threshold=0.3)
                
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
                        self.ssh_client.send_command(action)
                        self.move_count += 1
                        
                        # Wait for server to process the command (local needs more time)
                        logger.debug(f"Waiting 1 second for server to process '{action}'...")
                        time.sleep(1.0)
                        
                        # Read the response - wait for stable output
                        # Local subprocess needs more time than SSH
                        response = self.ssh_client.read_output_stable(timeout=3.5, stability_threshold=0.3)
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
                        
                        self.ssh_client.send_command('.')
                        self.move_count += 1
                        
                        # Wait for server to process (at least 2 seconds)
                        logger.debug("Waiting 3 seconds for server to process '.'...")
                        time.sleep(3.0)
                        
                        # Read the response with longer timeout
                        # Local subprocess needs more time than SSH
                        response = self.ssh_client.read_output(timeout=3.0)
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
            self.ssh_client.disconnect()

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
            self.ssh_client.send_command('E')
            time.sleep(2.0)  # Wait for response
            
            # Read experience screen
            exp_output = self.ssh_client.read_output(timeout=2.0)
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
                
                time.sleep(1.0)  # Let user see the stats
            else:
                logger.warning("No response to 'E' command")
            
            # Now send Ctrl-Q to quit
            logger.info("Sending Ctrl-Q to quit game...")
            self.ssh_client.send_command('\x11')  # Ctrl-Q
            time.sleep(0.5)
            
            # Read confirmation prompt
            output = self.ssh_client.read_output(timeout=2.0)
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
                        self.ssh_client.send_command('quit')
                        time.sleep(0.5)
                        self.ssh_client.send_command('\r')  # Send enter/return
                        time.sleep(1.0)
                    else:
                        # Generic confirmation prompt
                        logger.info("Confirming character abandon with 'y'...")
                        self.ssh_client.send_command('y')
                        time.sleep(1.0)
                    
                    # Capture end-of-game screens
                    logger.info("Capturing end-of-game state screens...")
                    for screen_num in range(5):  # Try to capture up to 5 screens
                        end_output = self.ssh_client.read_output(timeout=1.5)
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
                    self.ssh_client.send_command('quit')
                    time.sleep(0.5)
                    self.ssh_client.send_command('\r')  # Send enter
                    time.sleep(1.0)
            else:
                logger.warning("No response to Ctrl-Q, attempting to send 'quit' anyway")
                self.ssh_client.send_command('quit')
                time.sleep(0.5)
                self.ssh_client.send_command('\r')
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

    def _decide_action(self, output: str) -> Optional[str]:
        """
        Decide what action to take based on game state.
        
        CRITICAL: The output parameter should be the reconstructed screen text from pyte buffer
        (via screen_buffer.get_screen_text()), NOT raw PTY output. Raw PTY output contains only
        ANSI code deltas, not complete text needed for game state analysis.
        
        Uses the state machine to properly handle prompts and game phases.
        
        Strategy:
        1. Default: Auto-explore (o command)
        2. If enemy in range: Auto-engage with Tab
        3. If health < max and not in combat: Wait (.) each move until healed
        
        Args:
            output: Current game output (must be complete screen text from pyte buffer, not raw PTY)
            
        Returns:
            Command to send to the game
        """
        # Update state tracker
        state = self.state_tracker.update(output)
        logger.debug(f"State: {state}")
        
        # CHECK FOR ATTRIBUTE INCREASE PROMPT - LEVEL UP REWARD (CHECK FIRST)
        # When leveling up, player SOMETIMES gets to choose which stat to increase (Strength, Intelligence, Dexterity)
        # This is optional and not guaranteed - DCSS only shows this prompt sometimes
        # If it appears, respond ONCE per level (tracked by last_attribute_increase_level)
        clean_output = self._clean_ansi(output) if output else ""
        if 'Increase (S)trength' in clean_output or 'Increase (S)trength, (I)ntelligence, or (D)exterity' in clean_output:
            # Extract current level to check if this is a NEW attribute increase prompt
            current_level = self.parser.state.experience_level
            # Only respond if this is a NEW level (we haven't processed attribute increase for this level yet)
            if current_level and current_level > self.last_attribute_increase_level:
                self.last_attribute_increase_level = current_level
                logger.info("💪 Attribute increase prompt detected - choosing Strength (S)")
                return self._return_action('S', "Level-up: Increasing Strength")
            # Otherwise, skip this prompt (already handled for this level)
        
        # CHECK FOR LEVEL-UP MESSAGE - PRIORITY
        # When character gains a level, log the event and continue
        # Note: Stat increase prompt is OPTIONAL - DCSS doesn't always show it
        if self.parser.has_level_up_message(output):
            new_level = self.parser.extract_level_from_message(output)
            # Only process if this is a NEW level (avoid re-detecting same message on next turn)
            if new_level and new_level > self.last_level_up_processed:
                self.last_level_up_processed = new_level
                logger.info(f"🎉 LEVEL UP! Character reached Level {new_level}")
                # Check if there's a --more-- prompt to dismiss
                if '--more--' in output:
                    logger.info("Level-up message has --more-- prompt, dismissing...")
                    return self._return_action(' ', "Dismissing level-up --more-- prompt")  # Press space to dismiss the message
                else:
                    # Don't wait - continue gameplay. Stat increase prompt will be handled if it appears
                    logger.info("Level-up processed. Continuing gameplay (stat increase is optional)...")
                    return self._return_action('.', "Level-up processed")
        
        # CHECK FOR --MORE-- PROMPTS - DISMISS ONLY THIS SPECIFIC PROMPT
        # The game shows "--more--" when message buffer is full and needs clearing before showing additional information.
        # This is the ONLY automatic game prompt that should be dismissed without further context.
        # Generic prompt dismissal (for help text containing "press", etc) is NOT done here - only specific --more-- prompts.
        if '--more--' in output:
            logger.info("📄 More information prompt detected, pressing space to continue...")
            return self._return_action(' ', "Dismissing --more-- prompt")  # Press space to continue through any --more-- prompt
        
        # CHECK FOR "DONE EXPLORING" - DESCEND TO NEXT LEVEL USING GOTO
        # When auto-explore completes, use 'G' command to goto next dungeon level
        clean_output = self._clean_ansi(output) if output else ""
        if 'Done exploring' in clean_output and not self.waiting_for_goto_prompt:
            logger.info("📍 Done exploring current level! Preparing to descend to next level...")
            self._log_event('exploration', 'Level fully explored - descending')
            # Set up for goto command
            current_level = self.parser.state.dungeon_level
            self.goto_target_level = current_level + 1
            self.waiting_for_goto_prompt = True
            logger.info(f"Sending 'G' (goto) command to descend from level {current_level} to {self.goto_target_level}")
            return self._return_action('G', f"Descend to level {self.goto_target_level} (Done exploring)")
        
        # CHECK FOR GOTO PROMPT - SEND TARGET LEVEL
        # If we just sent 'G', we should get a prompt asking for the level
        if self.waiting_for_goto_prompt:
            logger.info(f"Handling goto prompt, sending target level: {self.goto_target_level}")
            self.waiting_for_goto_prompt = False
            # Send the target level as a string followed by Enter
            return self._return_action(str(self.goto_target_level), f"Descending to dungeon level {self.goto_target_level}")
        
        # If in menu, let the menu handler deal with it
        if self.state_tracker.in_menu_state():
            logger.info(f"📋 Menu detected - State: {state}, Waiting...")
            return self._return_action('.', "Waiting in menu")  # Wait in menu
        
        # CRITICAL: Check if screen shows gameplay indicators (Health, Time, XL, etc)
        # Even if state_tracker hasn't transitioned to GAMEPLAY yet
        # clean_output already extracted above for "Done exploring" check
        
        has_health = ('Health:' in output if output else False) or ('Health:' in clean_output)
        has_xl = ('XL:' in output if output else False) or ('XL:' in clean_output)
        
        # Also check for combat/action messages that indicate active gameplay
        has_combat_action = any(indicator in clean_output for indicator in [
            'You encounter', 'You see',  # Enemy encountered
            'block', 'miss', 'hits', 'damage',  # Combat happening
            'opens the door', 'You open',  # Movement
            'rat', 'bat', 'spider', 'goblin',  # Specific creatures
        ]) if clean_output else False
        
        has_gameplay_indicators = has_health or has_xl or has_combat_action
        
        # Also check if state machine detected gameplay via HUD indicators
        state_machine_detected_gameplay = self.char_creation_state.in_gameplay
        
        logger.debug(f"Gameplay check: Health:{has_health}, XL:{has_xl}, Combat:{has_combat_action}, StateMachine:{state_machine_detected_gameplay}")
        
        if has_gameplay_indicators or state_machine_detected_gameplay:
            logger.debug(f"Gameplay indicators detected (indicators={has_gameplay_indicators}, state_machine={state_machine_detected_gameplay}), proceeding with gameplay logic")
            self.gameplay_started = True  # Mark that we're in active gameplay
            # Continue to health/action logic below, skip state check
        elif self.gameplay_started:
            # We've already started gameplay, keep playing even if indicators aren't clear
            logger.debug(f"In active gameplay (started=True), proceeding with actions")
            # Continue to health/action logic below
        else:
            # Haven't reached gameplay yet - no indicators and not started
            logger.debug(f"Not in gameplay yet ({state}), auto-exploring until gameplay indicators appear")
            return self._return_action('o', "Auto-explore (waiting for gameplay to start)")
        
        # If we have output but no Time display, still try to play
        # (Some game states might not show Time display immediately)
        if not output:
            logger.debug("No output received, auto-exploring")
            return self._return_action('o', "No output - auto-exploring")
        
        # Parse the output to extract game state (health, etc)
        self.parser.parse_output(output)
        
        # Check if game is ready for input (has Time display)
        is_ready = self.parser.is_game_ready(output)
        logger.debug(f"Game ready status: {is_ready}")
        
        # Strategy Implementation:
        # 1. Check if enemy is in range FIRST (combat takes priority over everything)
        #    Do this BEFORE checking game_ready, since combat might not have Time display
        enemy_detected, enemy_name = self._detect_enemy_in_range(output)
        if enemy_detected:
            # Get current health percentage
            health = self.parser.state.health
            max_health = self.parser.state.max_health
            
            # Determine if we should use autofight or movement-based attacks
            if max_health > 0:
                health_percentage = (health / max_health) * 100
            else:
                health_percentage = 100
            
            # If health is 70% or below, use movement-based attacks instead of autofight
            # Autofight becomes unreliable when health is too low
            if health_percentage <= 70:
                logger.info(f"💔 Health at {health_percentage:.1f}% (≤70%) - Using manual movement attacks instead of autofight")
                direction = self._find_direction_to_enemy(output)
                return self._return_action(direction, f"Combat: Moving toward {enemy_name} (low health: {health_percentage:.1f}%)")
            
            # Check if we're too injured to fight recklessly (added safety check)
            clean_output = self._clean_ansi(output) if output else ""
            if 'too injured to fight recklessly' in clean_output.lower():
                logger.info("💔 Too injured to use autofight! Moving toward enemy instead...")
                direction = self._find_direction_to_enemy(output)
                return self._return_action(direction, "Combat: Too injured for autofight")
            
            logger.info(f"Enemy detected: {enemy_name} at {health_percentage:.1f}% health! Using autofight (Tab)")
            self.consecutive_rest_actions = 0  # Reset rest counter on combat
            return self._return_action('\t', f"Autofight - {enemy_name} in range")  # Tab = autofight
        
        # Even without Time display, if we have gameplay indicators proceed
        if not is_ready:
            logger.debug("Game ready status unclear, but proceeding with gameplay")
            # If we just sent Tab (autofight), don't send auto-explore yet - wait a turn
            if self.last_action_sent == '\t':
                logger.info("Waiting after autofight instead of auto-explore")
                return self._return_action('.', "Waiting after autofight")
            
            # Try to proceed with exploration
            logger.info("Using auto-explore")
            self.consecutive_rest_actions = 0
            return self._return_action('o', "Auto-explore")
        
        # 2. Check health status and decide between resting and exploring
        health = self.parser.state.health
        max_health = self.parser.state.max_health
        
        logger.debug(f"⚕️ Health check: {health}/{max_health}, consecutive_rests: {self.consecutive_rest_actions}/{self.max_consecutive_rests}")
        
        # Cache the last valid health reading for when updates don't include status line
        if max_health > 0:
            self.last_known_max_health = max_health
            self.last_known_health = health
            logger.debug(f"Updated health cache: {health}/{max_health}")
        elif self.last_known_max_health > 0:
            # Use cached health if we can't read current health but have cached values
            health = self.last_known_health
            max_health = self.last_known_max_health
            logger.debug(f"Using cached health: {health}/{max_health}")
        
        # If health cannot be read (0/0), request a screen redraw to get status info
        if health == 0 and max_health == 0:
            logger.warning("⚠️ Health display not readable (0/0). Requesting screen redraw...")
            return '\x12'  # Ctrl-R = redraw screen
        
        # Check if health is at least 60% of max health
        if max_health > 0:
            health_percentage = (health / max_health) * 100
            logger.debug(f"Health: {health_percentage:.1f}% ({health}/{max_health})")
            
            # If health is above 60%, auto-explore (but not right after autofight command)
            if health_percentage >= 60:
                # If we just sent Tab (autofight), don't immediately send auto-explore
                # Wait one turn instead to let the game process autofight
                if self.last_action_sent == '\t':
                    logger.info(f"⏸️ Waiting after autofight (health: {health_percentage:.1f}%)")
                    return self._return_action('.', f"Waiting after autofight")
                
                logger.info(f"🗺️ Auto-explore action (health: {health_percentage:.1f}%)")
                self.consecutive_rest_actions = 0
                return self._return_action('o', f"Auto-explore (health: {health_percentage:.1f}%)")
            else:
                # Health is below 90%, rest to recover
                logger.info(f"😴 Resting to recover (health: {health_percentage:.1f}%)")
                self.consecutive_rest_actions += 1
                return self._return_action('5', f"Resting to recover (health: {health_percentage:.1f}%)")
        
        # If we can't determine max health, default to auto-explore
        logger.warning(f"⚠️ Cannot determine max health, defaulting to auto-explore")
        self.consecutive_rest_actions = 0
        return self._return_action('o', "Auto-explore (health unknown)")
    
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
            output = self.ssh_client.read_output(timeout=3.0)
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
                    output = self.ssh_client.read_output(timeout=2.0)
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
                        self.ssh_client.send_command('\x15')  # Ctrl+U
                        time.sleep(0.1)
                        
                        # Send name as individual keypresses in cbreak mode
                        for char in name:
                            self.ssh_client.send_command(char)
                            time.sleep(0.05)  # Small delay between characters
                        # Send Enter (\r\n for compatibility)
                        self.ssh_client.send_command('\r\n')
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
                            self.ssh_client.send_command(selection_key)
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
            output = self.ssh_client.read_output(timeout=2.0)
            
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
                invalid_symbols = ['Found', 'You', 'The', 'This', 'That', 'Your', 'And', 'Are', 'But', 'Can', 'For', 'Have', 'Here', 'Just', 'Know', 'Like', 'Make', 'More', 'Now', 'Only', 'Out', 'Over', 'Some', 'Such', 'Take', 'Want', 'Way', 'What', 'When', 'Will', 'With', 'Would', 'have']
                if symbols in invalid_symbols:
                    continue
                
                # Validate the entry
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

    def _find_direction_to_enemy(self, output: str) -> str:
        """
        Find the nearest visible enemy and return the direction to move toward it.
        
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
        
        # Try to find map in current output first, fall back to last screen if not found
        lines = output.split('\n')
        player_pos = None
        enemies = []
        
        # Find player position (@) and enemy positions (lowercase letters)
        # IMPORTANT: Only scan the map area (left ~80 chars, rows 0-25) to avoid UI elements on the right
        # The status panel on the right contains text like "o)", "d)", etc. that aren't real enemies
        for y, line in enumerate(lines):
            if y > 25:  # Map area is roughly rows 0-25, status panel is on the right
                continue
            # Only scan up to column 80 to avoid status panel on the right
            for x in range(min(80, len(line))):
                char = line[x]
                if char == '@':
                    player_pos = (x, y)
                # Enemy characters are lowercase letters (excluding dungeon characters)
                # Note: Exclude specific UI letters like 'o', 'd' that appear in sidebars
                elif char.islower() and char not in '.+=#-~,|odiabxpqmwc':
                    enemies.append((x, y, char))
        
        # If we couldn't find the map in current output, try the last screen
        if not player_pos and self.last_screen:
            logger.debug("Map not found in current output, using last screen")
            lines = self.last_screen.split('\n')
            for y, line in enumerate(lines):
                if y > 25:
                    continue
                for x in range(min(80, len(line))):
                    char = line[x]
                    if char == '@':
                        player_pos = (x, y)
                    elif char.islower() and char not in '.+=#-~,|odiabxpqmwc':
                        enemies.append((x, y, char))
        
        if not player_pos or not enemies:
            logger.debug(f"Could not find player or enemies on map (player_pos={player_pos}, enemies={len(enemies)})")
            return '.'
        
        # Find the nearest enemy
        player_x, player_y = player_pos
        nearest_enemy = None
        nearest_distance = float('inf')
        
        for enemy_x, enemy_y, enemy_char in enemies:
            # Calculate distance
            distance = abs(enemy_x - player_x) + abs(enemy_y - player_y)  # Manhattan distance
            if distance < nearest_distance and distance > 0:  # Exclude player's own position
                nearest_distance = distance
                nearest_enemy = (enemy_x, enemy_y, enemy_char)
        
        if not nearest_enemy:
            logger.debug("No reachable enemy found")
            return '.'
        
        enemy_x, enemy_y, enemy_char = nearest_enemy
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
        
        direction = direction_map.get((dx, dy), '.')
        # Enhanced logging with detected enemy symbol for debugging
        logger.debug(f"Map scan found enemy '{enemy_char}' at ({enemy_x}, {enemy_y}), player at ({player_x}, {player_y}), distance={nearest_distance}")
        logger.info(f"🎯 Moving toward {enemy_char} (distance: {nearest_distance}, direction: {direction})")
        return self._return_action(direction, f"Moving toward {enemy_char}")

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

