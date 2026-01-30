"""
Example usage of python-statemachine enhanced state machines and blessed display.

This file demonstrates how to use the new modules in your bot.
"""

from char_creation_state_machine import CharacterCreationStateMachine
from game_state_machine import GameStateMachine
from bot_display import BotDisplay, DebugDisplay
from loguru import logger


def example_character_creation():
    """Example: Using the character creation state machine."""
    print("\n=== Character Creation State Machine Example ===\n")
    
    # Create state machine
    sm = CharacterCreationStateMachine()
    
    # Simulate screen updates during character creation
    screens = [
        "Select your species: [a] Human [b] Dwarf [c] Elf",
        "Select your class: [a] Fighter [b] Mage [c] Rogue",
        "Select your background: [a] Soldier [b] Scholar",
        "HP: 20/20 AC: 5 EXP: 1 Level: 1",
    ]
    
    for i, screen in enumerate(screens, 1):
        state = sm.update(screen)
        print(f"Screen {i}: State = {state}")
        print(f"  Stuck: {sm.is_stuck}, In Gameplay: {sm.in_gameplay}")
        if i == len(screens):
            print(f"  Ready for gameplay: {sm.in_gameplay}")


def example_game_state_machine():
    """Example: Using the new game state machine."""
    print("\n=== Game State Machine Example ===\n")
    
    # Create state machine
    sm = GameStateMachine()
    
    # Simulate game progression
    print(f"Initial state: {sm.current_state.id}")
    
    # Connect to game
    sm.connect()
    print(f"After connect: {sm.current_state.id}")
    
    # Start game
    sm.start_game()
    print(f"After start_game: {sm.current_state.id}")
    
    # Simulate gameplay
    screen1 = "Level 1 HP: 15/20 AC: 5 Exp: 1"
    sm.update(screen1)
    print(f"Gameplay screen: {sm.current_state.id}")
    
    # Enter menu
    screen2 = "Level 1 HP: 15/20 [a] Ability [b] Cast"
    sm.update(screen2)
    print(f"Menu screen: {sm.current_state.id}")
    
    # Exit menu back to gameplay
    screen3 = "Level 1 HP: 15/20 AC: 5"
    sm.update(screen3)
    print(f"Back to gameplay: {sm.current_state.id}")


def example_blessed_display():
    """Example: Using blessed for colored terminal output."""
    print("\n=== Blessed Display Example ===\n")
    
    # Create display
    display = BotDisplay()
    
    # Display various formatted messages
    print(display.header("DCSS Bot Started"))
    
    print(display.section("Game Status"))
    print(display.success("Connected to Crawl"))
    print(display.info("Navigating character creation"))
    
    print("\n" + display.section("Game State"))
    state_info = {
        "state": "GAMEPLAY",
        "health": 18,
        "max_health": 20,
        "mana": 10,
        "max_mana": 15,
        "exp_level": 3,
        "exp_progress": 45,
        "gold": 250,
        "hunger": "satisfied",
        "location": "D:2",
    }
    print(display.game_state_display(state_info))
    
    print("\n" + display.section("Actions"))
    print(display.action_display("Move", "East"))
    print(display.action_display("Attack", "Goblin"))
    print(display.action_display("Rest", "HP restoration"))
    
    print("\n" + display.move_count(42, 15.5))


def example_debug_display():
    """Example: Using debug display for development."""
    print("\n=== Debug Display Example ===\n")
    
    display = DebugDisplay()
    
    # Show state machine debug info
    history = ["start", "race", "class", "background"]
    print(display.state_machine_debug("background", False, history))
    
    print("\n")
    
    # Show performance stats
    print(display.performance_stats(100, 45.5, 2.2))
    
    print("\n")
    
    # Show screen capture info
    print(display.screen_capture_info(160, 40, 35))


def example_integration():
    """Example: Integrating state machines and display."""
    print("\n=== Full Integration Example ===\n")
    
    # Create components
    char_sm = CharCreationSMv2()
    game_sm = GameStateMachine()
    display = BotDisplay()
    debug_display = DebugDisplay()
    
    print(display.header("Bot Initialization"))
    
    # Character creation phase
    print(display.section("Character Creation"))
    print(display.info("Navigating startup menus"))
    
    screens = [
        "Select your species: [a] Human",
        "Select your class: [a] Fighter",
        "HP: 15/15 AC: 5",
    ]
    
    for screen in screens:
        state = char_sm.update(screen)
        print(display.action_display(f"Update state", state))
        
        if char_sm.in_gameplay:
            print(display.success("Character ready for gameplay!"))
            break
    
    # Gameplay phase
    print("\n" + display.section("Gameplay"))
    game_sm.connect()
    game_sm.start_game()
    
    gameplay_screens = [
        "Level 1 HP: 15/15 AC: 5 Exp: 1",
        "Level 1 HP: 14/15 AC: 5 Exp: 2",
        "Level 1 HP: 14/15 [a] Ability [b] Cast",
    ]
    
    for i, screen in enumerate(gameplay_screens, 1):
        game_sm.update(screen)
        
        state_info = {
            "state": game_sm.current_state.id.upper(),
            "health": 15 - (i - 1),
            "max_health": 15,
            "exp_level": 1,
            "exp_progress": i * 10,
        }
        
        print(display.game_state_display(state_info))
        print(display.action_display(f"Turn {i}", game_sm.current_state.id))
    
    print(display.separator("═"))


if __name__ == "__main__":
    # Run all examples
    example_character_creation()
    example_game_state_machine()
    example_blessed_display()
    example_debug_display()
    example_integration()
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
