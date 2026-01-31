"""Unified TUI display combining Crawl game output with bot activity panel."""

import sys
from collections import deque
from typing import Optional, List
from datetime import datetime
from loguru import logger


class UnifiedBotDisplay:
    """
    Displays Crawl game output with a bot activity panel below it.
    
    Layout:
    - Top: Full Crawl game TUI
    - Bottom: 12-line activity/debug panel with latest bot messages
    """
    
    # 12-line activity panel (adjustable)
    ACTIVITY_PANEL_HEIGHT = 12
    
    def __init__(self, max_messages: int = 100):
        """
        Initialize unified display.
        
        Args:
            max_messages: Maximum activity messages to keep in history
        """
        self.activity_messages: deque = deque(maxlen=max_messages)
        self.last_move = 0
        self.last_action = ""
        self.current_state = ""
        self.health_info = ""
        
    def add_activity(self, message: str, level: str = "info") -> None:
        """
        Add a message to the activity log.
        
        Args:
            message: Activity message to display
            level: Message level - "info", "debug", "warning", "error", "success"
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format message with level indicator
        if level == "success":
            prefix = "✓"
            formatted_msg = f"[{timestamp}] {prefix} {message}"
        elif level == "warning":
            prefix = "⚠"
            formatted_msg = f"[{timestamp}] {prefix} {message}"
        elif level == "error":
            prefix = "✗"
            formatted_msg = f"[{timestamp}] {prefix} {message}"
        elif level == "debug":
            prefix = "⚙"
            formatted_msg = f"[{timestamp}] {prefix} {message}"
        else:  # info
            prefix = "ℹ"
            formatted_msg = f"[{timestamp}] {prefix} {message}"
        
        self.activity_messages.append((formatted_msg, level))
        logger.debug(f"Activity: {formatted_msg}")
    
    def display(self, visual_screen: str, move_count: int = 0, action: str = "", 
                state: str = "", health: str = "") -> None:
        """
        Display the unified interface: game screen + activity panel.
        
        Args:
            visual_screen: Full accumulated game screen from pyte buffer
            move_count: Current move number
            action: Current action being performed
            state: Current game state
            health: Health/mana/level info string
        """
        if not visual_screen or not visual_screen.strip():
            return
        
        try:
            # Store state for later reference
            self.last_move = move_count
            self.last_action = action
            self.current_state = state
            self.health_info = health
            
            # Clear screen
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            
            # Calculate available space
            # Get terminal height
            try:
                import shutil
                _, term_height = shutil.get_terminal_size(fallback=(160, 40))
            except Exception:
                term_height = 40
            
            # Reserve space for activity panel + separator
            game_display_height = max(10, term_height - self.ACTIVITY_PANEL_HEIGHT - 4)
            
            # Split game screen to fit available space
            game_lines = visual_screen.split('\n')
            game_lines = game_lines[-game_display_height:] if len(game_lines) > game_display_height else game_lines
            
            # Display game output
            sys.stdout.write("\033[0m")  # Reset colors
            sys.stdout.write('\n'.join(game_lines))
            sys.stdout.flush()
            
            # Display activity panel on a new line
            sys.stdout.write("\n")
            self._display_activity_panel()
            
        except Exception as e:
            logger.error(f"Error displaying unified TUI: {e}")
    
    def _display_activity_panel(self) -> None:
        """Display the 12-line bot activity panel."""
        try:
            # Panel header
            panel_header = f"BOT ACTIVITY ({len(self.activity_messages)} messages)"
            sys.stdout.write(f"\033[0m\033[1;36m{panel_header}\033[0m\n")  # Bold cyan
            
            # Separator
            sys.stdout.write("-" * 120 + "\n")
            
            # Get the last N messages to fit in panel
            # Account for header, separator, and top/bottom padding
            available_lines = self.ACTIVITY_PANEL_HEIGHT - 3
            
            # Get most recent messages
            messages_to_show = list(self.activity_messages)[-available_lines:]
            
            # Pad with empty lines if needed
            while len(messages_to_show) < available_lines:
                messages_to_show.insert(0, ("", "info"))
            
            # Display messages with color coding
            for msg, level in messages_to_show:
                if msg:
                    if level == "success":
                        colored_msg = f"\033[32m{msg}\033[0m"  # Green
                    elif level == "warning":
                        colored_msg = f"\033[33m{msg}\033[0m"  # Yellow
                    elif level == "error":
                        colored_msg = f"\033[31m{msg}\033[0m"  # Red
                    elif level == "debug":
                        colored_msg = f"\033[36m{msg}\033[0m"  # Cyan
                    else:  # info
                        colored_msg = msg
                    
                    # Truncate to terminal width if needed
                    if len(msg) > 118:
                        colored_msg = colored_msg[:115] + "..."
                    
                    sys.stdout.write(f"{colored_msg}\n")
                else:
                    sys.stdout.write("\n")
            
            # Bottom separator
            sys.stdout.write("-" * 120 + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Error displaying activity panel: {e}")
    
    def display_activity_only(self) -> None:
        """
        Display just the activity panel (for quick updates without full screen redraw).
        Useful when not showing game screen.
        """
        try:
            sys.stdout.write("\033[2J\033[H")  # Clear and home
            sys.stdout.flush()
            
            sys.stdout.write(f"\033[1;36mBOT ACTIVITY\033[0m\n")  # Bold cyan header
            sys.stdout.write("-" * 120 + "\n")
            
            # Show last N messages
            available_lines = 30
            messages_to_show = list(self.activity_messages)[-available_lines:]
            
            for msg, level in messages_to_show:
                if level == "success":
                    sys.stdout.write(f"\033[32m{msg}\033[0m\n")  # Green
                elif level == "warning":
                    sys.stdout.write(f"\033[33m{msg}\033[0m\n")  # Yellow
                elif level == "error":
                    sys.stdout.write(f"\033[31m{msg}\033[0m\n")  # Red
                elif level == "debug":
                    sys.stdout.write(f"\033[36m{msg}\033[0m\n")  # Cyan
                else:
                    sys.stdout.write(f"{msg}\n")
            
            sys.stdout.write("-" * 120 + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Error displaying activity panel: {e}")
    
    def get_activity_history(self, count: int = 50) -> List[str]:
        """
        Get recent activity messages.
        
        Args:
            count: Number of messages to return
            
        Returns:
            List of recent activity messages
        """
        messages = list(self.activity_messages)[-count:]
        return [msg for msg, _ in messages]
    
    def clear_activity(self) -> None:
        """Clear all activity messages."""
        self.activity_messages.clear()
