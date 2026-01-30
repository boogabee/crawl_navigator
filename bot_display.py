"""Terminal display utilities using blessed for enhanced output."""

from blessed import Terminal
from typing import Optional, Dict, Any
from loguru import logger


class BotDisplay:
    """Manages terminal display with colors and formatting."""
    
    def __init__(self, width: int = None, height: int = None):
        """
        Initialize display manager.
        
        Args:
            width: Terminal width (auto-detect if None)
            height: Terminal height (auto-detect if None)
        """
        self.term = Terminal()
        self.width = width or self.term.width or 160
        self.height = height or self.term.height or 40
        self.supports_color = self.term.does_styling
        
    def header(self, text: str) -> str:
        """Format text as header."""
        if self.supports_color:
            return self.term.bold_bright_blue(f"\n{'='*60}\n{text}\n{'='*60}\n")
        return f"\n{'='*60}\n{text}\n{'='*60}\n"
    
    def section(self, title: str, content: str = "") -> str:
        """Format text as section."""
        if self.supports_color:
            header = self.term.bold_cyan(f"\n>>> {title}")
            return f"{header}\n{content}" if content else header
        return f"\n>>> {title}\n{content}" if content else f"\n>>> {title}"
    
    def success(self, text: str) -> str:
        """Format successful message."""
        if self.supports_color:
            return self.term.green(f"✓ {text}")
        return f"✓ {text}"
    
    def warning(self, text: str) -> str:
        """Format warning message."""
        if self.supports_color:
            return self.term.yellow(f"⚠ {text}")
        return f"⚠ {text}"
    
    def error(self, text: str) -> str:
        """Format error message."""
        if self.supports_color:
            return self.term.bold_red(f"✗ {text}")
        return f"✗ {text}"
    
    def info(self, text: str) -> str:
        """Format info message."""
        if self.supports_color:
            return self.term.cyan(f"ℹ {text}")
        return f"ℹ {text}"
    
    def status(self, label: str, value: Any, color: str = "white") -> str:
        """Format status line with label and value."""
        if self.supports_color:
            label_str = self.term.bold(label)
            if color == "green":
                value_str = self.term.green(str(value))
            elif color == "yellow":
                value_str = self.term.yellow(str(value))
            elif color == "red":
                value_str = self.term.bold_red(str(value))
            elif color == "cyan":
                value_str = self.term.cyan(str(value))
            else:
                value_str = str(value)
            return f"{label_str}: {value_str}"
        return f"{label}: {value}"
    
    def game_state_display(self, state_info: Dict[str, Any]) -> str:
        """
        Display current game state with colors.
        
        Args:
            state_info: Dictionary with state information
            
        Returns:
            Formatted display string
        """
        lines = []
        
        # Header
        lines.append(self.section("GAME STATE"))
        
        # State name
        state = state_info.get("state", "UNKNOWN")
        state_color = "green" if state == "GAMEPLAY" else "yellow" if state == "MENU" else "red"
        lines.append(self.status("State", state, state_color))
        
        # Health display
        health = state_info.get("health", 0)
        max_health = state_info.get("max_health", 0)
        health_color = "red" if health < max_health * 0.25 else "yellow" if health < max_health * 0.5 else "green"
        lines.append(self.status("Health", f"{health}/{max_health}", health_color))
        
        # Mana display
        mana = state_info.get("mana", 0)
        max_mana = state_info.get("max_mana", 0)
        if max_mana > 0:
            mana_color = "cyan"
            lines.append(self.status("Mana", f"{mana}/{max_mana}", mana_color))
        
        # Experience
        exp_level = state_info.get("exp_level", 1)
        exp_progress = state_info.get("exp_progress", 0)
        lines.append(self.status("Level", exp_level, "cyan"))
        lines.append(self.status("Exp Progress", f"{exp_progress}%", "cyan"))
        
        # Location
        if "location" in state_info:
            lines.append(self.status("Location", state_info["location"], "white"))
        
        # Gold
        if "gold" in state_info:
            lines.append(self.status("Gold", state_info["gold"], "yellow"))
        
        # Hunger
        if "hunger" in state_info:
            lines.append(self.status("Hunger", state_info["hunger"], "white"))
        
        return "\n".join(lines)
    
    def action_display(self, action: str, details: str = "") -> str:
        """
        Display bot action.
        
        Args:
            action: Action being performed
            details: Additional details
            
        Returns:
            Formatted action display
        """
        if self.supports_color:
            action_str = self.term.bold_white(action)
            details_str = self.term.dim(f" ({details})") if details else ""
            return f"→ {action_str}{details_str}"
        return f"→ {action} ({details})" if details else f"→ {action}"
    
    def move_count(self, count: int, elapsed: float = None) -> str:
        """Display move counter."""
        if elapsed:
            if self.supports_color:
                return self.term.bold_green(f"Move {count} | {elapsed:.1f}s")
            return f"Move {count} | {elapsed:.1f}s"
        if self.supports_color:
            return self.term.bold_green(f"Move {count}")
        return f"Move {count}"
    
    def separator(self, char: str = "-") -> str:
        """Display separator line."""
        if self.supports_color:
            return self.term.dim(char * (self.width - 10))
        return char * (self.width - 10)
    
    def clear_screen(self) -> str:
        """Clear terminal screen."""
        return self.term.clear()
    
    def move_cursor(self, x: int, y: int) -> str:
        """Move cursor to position."""
        return self.term.move(y, x)
    
    def hide_cursor(self) -> str:
        """Hide cursor."""
        return self.term.hide_cursor()
    
    def show_cursor(self) -> str:
        """Show cursor."""
        return self.term.show_cursor()


class DebugDisplay(BotDisplay):
    """Extended display for debugging information."""
    
    def state_machine_debug(self, state_name: str, is_stuck: bool, history: list) -> str:
        """
        Display state machine debug info.
        
        Args:
            state_name: Current state name
            is_stuck: Whether state machine is stuck
            history: State history
            
        Returns:
            Formatted debug display
        """
        lines = []
        lines.append(self.section("STATE MACHINE DEBUG"))
        
        stuck_indicator = self.warning("STUCK!") if is_stuck else self.success("OK")
        lines.append(f"Status: {stuck_indicator}")
        
        lines.append(self.status("Current State", state_name, "cyan"))
        
        # Show recent history
        recent = history[-5:] if len(history) > 5 else history
        history_str = " → ".join(recent)
        if self.supports_color:
            lines.append(f"History: {self.term.dim(history_str)}")
        else:
            lines.append(f"History: {history_str}")
        
        return "\n".join(lines)
    
    def performance_stats(self, moves: int, elapsed: float, actions_per_second: float) -> str:
        """
        Display performance statistics.
        
        Args:
            moves: Total moves made
            elapsed: Time elapsed in seconds
            actions_per_second: Speed metric
            
        Returns:
            Formatted stats display
        """
        lines = []
        lines.append(self.section("PERFORMANCE STATS"))
        
        lines.append(self.status("Total Moves", moves, "green"))
        lines.append(self.status("Elapsed Time", f"{elapsed:.1f}s", "cyan"))
        lines.append(self.status("Speed", f"{actions_per_second:.2f} actions/sec", "yellow"))
        
        return "\n".join(lines)
    
    def screen_capture_info(self, width: int, height: int, lines_captured: int) -> str:
        """
        Display screen capture debug info.
        
        Args:
            width: Screen width
            height: Screen height
            lines_captured: Number of lines captured
            
        Returns:
            Formatted info display
        """
        lines = []
        lines.append(self.section("SCREEN CAPTURE"))
        
        lines.append(self.status("Resolution", f"{width}x{height}", "cyan"))
        lines.append(self.status("Lines Captured", lines_captured, "green"))
        
        return "\n".join(lines)


class ScreenBuffer:
    """ANSI screen buffer display using blessed."""
    
    def __init__(self, width: int = 160, height: int = 40):
        """Initialize screen buffer display."""
        self.term = Terminal()
        self.width = width
        self.height = height
        self.display = BotDisplay(width, height)
        
    def show_screen(self, screen_text: str) -> None:
        """
        Display game screen with formatting.
        
        Args:
            screen_text: Screen content to display
        """
        lines = screen_text.split('\n')
        for i, line in enumerate(lines[:self.height]):
            # Trim to terminal width
            display_line = line[:self.width]
            print(display_line)
    
    def show_formatted_screen(self, screen_text: str, state: str = "UNKNOWN") -> None:
        """
        Display game screen with state indication.
        
        Args:
            screen_text: Screen content
            state: Current game state
        """
        print(self.display.separator("═"))
        print(self.display.section(f"GAME SCREEN ({state})"))
        print(self.display.separator("─"))
        self.show_screen(screen_text)
        print(self.display.separator("═"))
