"""
Decision engine for DCSS bot - replaces 1200+ line _decide_action() method.

This module provides a rule-based engine that evaluates game conditions in priority order
to determine the next action. Each rule encapsulates a specific decision pattern.

Architecture:
- Rule: Individual decision with condition and action
- DecisionContext: Game state snapshot for evaluation
- DecisionEngine: Evaluates rules in priority order
- Priority: Lower priority value = higher importance (evaluated first)
"""

from typing import Optional, Callable, Any, List, Dict
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class Priority(Enum):
    """Priority levels for decision rules."""
    CRITICAL = 1      # Immediate threats, menu prompts
    URGENT = 5        # Damage recovery, level-up
    HIGH = 10         # Combat, equipment
    NORMAL = 20       # Exploration, items
    LOW = 30          # Optional actions


@dataclass
class DecisionContext:
    """Game state context for decision evaluation."""
    # Raw output (for legacy compatibility)
    output: str
    
    # Parsed state
    health: int
    max_health: int
    level: int
    dungeon_level: int
    
    # Detection results
    enemy_detected: bool
    enemy_name: str
    items_on_ground: bool
    in_shop: bool
    in_inventory_screen: bool
    in_item_pickup_menu: bool
    in_menu: bool
    
    # Flags
    equip_slot_pending: bool
    quaff_slot_pending: bool
    has_level_up: bool
    has_more_prompt: bool
    attribute_increase_prompt: bool
    save_game_prompt: bool
    
    # Previous state
    last_action_sent: str
    last_level_up_processed: int
    last_attribute_increase_level: int
    last_equipment_check: int
    last_inventory_refresh: int
    move_count: int
    
    # Complex state
    has_gameplay_indicators: bool
    gameplay_started: bool
    goto_state: Optional[str]
    goto_target_level: int
    
    @property
    def health_percentage(self) -> float:
        """Calculate health percentage."""
        if self.max_health <= 0:
            return 100.0
        return (self.health / self.max_health) * 100


@dataclass
class Rule:
    """
    A single decision rule: if condition is true, execute action.
    
    Attributes:
        name: Human-readable rule name
        priority: Priority.VALUE - lower values evaluated first
        condition: Function that takes DecisionContext and returns bool
        action: Function that takes DecisionContext and returns (command, reason)
    """
    name: str
    priority: Priority
    condition: Callable[[DecisionContext], bool]
    action: Callable[[DecisionContext], tuple[str, str]]


class DecisionEngine:
    """
    Rule-based decision engine for action selection.
    
    Usage:
        engine = DecisionEngine()
        engine.add_rule(Rule(...))
        command, reason = engine.decide(context)
    """
    
    def __init__(self):
        """Initialize the decision engine with no rules."""
        self.rules: List[Rule] = []
    
    def add_rule(self, rule: Rule) -> 'DecisionEngine':
        """Add a rule to the engine. Returns self for chaining."""
        self.rules.append(rule)
        return self
    
    def decide(self, context: DecisionContext) -> tuple[Optional[str], str]:
        """
        Evaluate rules in priority order and return the first matching action.
        
        Args:
            context: Game state context
            
        Returns:
            (command, reason) tuple or (None, "") if no rules match
        """
        # Sort rules by priority (lower priority value = higher importance)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority.value)
        
        logger.debug(f"Evaluating {len(sorted_rules)} rules in priority order")
        
        for rule in sorted_rules:
            try:
                if rule.condition(context):
                    logger.debug(f"✓ Rule matched: {rule.name}")
                    command, reason = rule.action(context)
                    return command, reason
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
                continue
        
        # No rules matched - should not happen if engine is properly configured
        logger.warning("No decision rules matched - this should not happen")
        return None, "No matching rules"


def create_default_engine() -> DecisionEngine:
    """
    Create the standard decision engine with all game rules.
    
    This replaces the 1200-line _decide_action() method by defining
    each decision pattern as a separate rule.
    """
    engine = DecisionEngine()
    
    # CRITICAL PRIORITY: Menu prompts and immediate threats
    
    # Rule: Respond to equip slot prompt
    engine.add_rule(Rule(
        name="Equip slot prompt",
        priority=Priority.CRITICAL,
        condition=lambda ctx: ctx.equip_slot_pending,
        action=lambda ctx: ("", "")  # Will be handled by caller with stored slot
    ))
    
    # Rule: Respond to quaff slot prompt
    engine.add_rule(Rule(
        name="Quaff slot prompt",
        priority=Priority.CRITICAL,
        condition=lambda ctx: ctx.quaff_slot_pending,
        action=lambda ctx: ("", "")  # Will be handled by caller with stored slot
    ))
    
    # Rule: Handle attribute increase prompt
    engine.add_rule(Rule(
        name="Attribute increase prompt",
        priority=Priority.CRITICAL,
        condition=lambda ctx: ctx.attribute_increase_prompt and ctx.level > ctx.last_attribute_increase_level,
        action=lambda ctx: ('S', "Level-up: Increasing Strength")
    ))
    
    # Rule: Reject save game prompt
    engine.add_rule(Rule(
        name="Save game prompt",
        priority=Priority.CRITICAL,
        condition=lambda ctx: ctx.save_game_prompt,
        action=lambda ctx: ('n', "Rejecting save prompt - continuing gameplay")
    ))
    
    # Rule: Dismiss --more-- prompt
    engine.add_rule(Rule(
        name="More prompt",
        priority=Priority.CRITICAL,
        condition=lambda ctx: ctx.has_more_prompt,
        action=lambda ctx: (' ', "Dismissing --more-- prompt")
    ))
    
    # Rule: Request screen redraw when health is unreadable
    engine.add_rule(Rule(
        name="Screen redraw (health unreadable)",
        priority=Priority.CRITICAL,
        condition=lambda ctx: ctx.health == 0 and ctx.max_health == 0,
        action=lambda ctx: ('\x12', "Requesting screen redraw (health display missing)")
    ))
    
    # HIGH PRIORITY: Shop and menu handling
    
    # Rule: Exit shop
    engine.add_rule(Rule(
        name="Shop detected",
        priority=Priority.HIGH,
        condition=lambda ctx: ctx.in_shop,
        action=lambda ctx: ('\x1b', "Exiting shop (not buying)")
    ))
    
    # Rule: Handle item pickup menu
    engine.add_rule(Rule(
        name="Item pickup menu",
        priority=Priority.HIGH,
        condition=lambda ctx: ctx.in_item_pickup_menu,
        action=lambda ctx: ("", "")  # Will be handled by caller
    ))
    
    # Rule: Handle inventory screen
    engine.add_rule(Rule(
        name="Inventory screen",
        priority=Priority.HIGH,
        condition=lambda ctx: ctx.in_inventory_screen,
        action=lambda ctx: ("", "")  # Will be handled by caller
    ))
    
    # Rule: Handle in-menu state
    engine.add_rule(Rule(
        name="In menu",
        priority=Priority.HIGH,
        condition=lambda ctx: ctx.in_menu,
        action=lambda ctx: ('.', "Waiting in menu")
    ))
    
    # URGENT PRIORITY: Level-up and damage recovery
    
    # Rule: Handle level-up with --more-- prompt
    engine.add_rule(Rule(
        name="Level-up with more prompt",
        priority=Priority.URGENT,
        condition=lambda ctx: ctx.has_level_up and ctx.has_more_prompt and ctx.level > ctx.last_level_up_processed,
        action=lambda ctx: (' ', "Dismissing level-up --more-- prompt")
    ))
    
    # Rule: Handle level-up without --more--
    engine.add_rule(Rule(
        name="Level-up",
        priority=Priority.URGENT,
        condition=lambda ctx: ctx.has_level_up and ctx.level > ctx.last_level_up_processed,
        action=lambda ctx: ('.', "Level-up processed")
    ))
    
    # Rule: Grab items on ground
    engine.add_rule(Rule(
        name="Items on ground",
        priority=Priority.URGENT,
        condition=lambda ctx: ctx.items_on_ground,
        action=lambda ctx: ('g', "Grabbing items from ground")
    ))
    
    # Rule: Equip better armor
    engine.add_rule(Rule(
        name="Better armor available",
        priority=Priority.URGENT,
        condition=lambda ctx: False,  # Will be checked by caller with frequency
        action=lambda ctx: ("", "")
    ))
    
    # Rule: Identify untested potions
    engine.add_rule(Rule(
        name="Untested potions",
        priority=Priority.URGENT,
        condition=lambda ctx: False,  # Will be checked by caller with frequency
        action=lambda ctx: ("", "")
    ))
    
    # NORMAL PRIORITY: Combat
    
    # Rule: Combat with low health - move toward enemy to engage
    # Note: When health is low, DCSS disables autofight (TAB) command.
    # Must manually move toward the enemy to fight. Using 'l' (move right)
    # as default direction; will need direction calculation later for better accuracy.
    engine.add_rule(Rule(
        name="Combat (low health - move to engage)",
        priority=Priority.NORMAL,
        condition=lambda ctx: ctx.enemy_detected and ctx.health_percentage <= 70,
        action=lambda ctx: ('l', f"Moving toward {ctx.enemy_name} to engage (low health: {ctx.health_percentage:.1f}%)")
    ))
    
    # Rule: Combat with normal health - autofight
    engine.add_rule(Rule(
        name="Combat (autofight)",
        priority=Priority.NORMAL,
        condition=lambda ctx: ctx.enemy_detected and ctx.health_percentage > 70,
        action=lambda ctx: ('\t', f"Autofight - {ctx.enemy_name} in range")
    ))
    
    # NORMAL PRIORITY: Goto (level descent)
    # Note: Goto command will be checked by caller, not by engine rules
    # (requires checking message log for "Done exploring" text)
    
    # Rule: Respond to goto location type prompt
    engine.add_rule(Rule(
        name="Goto location type",
        priority=Priority.NORMAL,
        condition=lambda ctx: ctx.goto_state == 'awaiting_location_type',
        action=lambda ctx: ('D', "Selecting Dungeon from goto location menu")
    ))
    
    # Rule: Respond to goto level number prompt
    engine.add_rule(Rule(
        name="Goto level number",
        priority=Priority.NORMAL,
        condition=lambda ctx: ctx.goto_state == 'awaiting_level_number',
        action=lambda ctx: (str(ctx.goto_target_level), f"Descending to dungeon level {ctx.goto_target_level}")
    ))
    
    # NORMAL PRIORITY: Health-based decisions
    
    # Rule: Rest after autofight
    engine.add_rule(Rule(
        name="Rest after autofight",
        priority=Priority.NORMAL,
        condition=lambda ctx: ctx.last_action_sent == '\t' and not ctx.enemy_detected,
        action=lambda ctx: ('.', "Waiting after autofight")
    ))
    
    # Rule: Explore with good health
    engine.add_rule(Rule(
        name="Explore (good health)",
        priority=Priority.NORMAL,
        condition=lambda ctx: ctx.has_gameplay_indicators and ctx.health_percentage >= 60,
        action=lambda ctx: ('o', f"Auto-explore (health: {ctx.health_percentage:.1f}%)")
    ))
    
    # Rule: Rest to recover
    engine.add_rule(Rule(
        name="Rest to recover",
        priority=Priority.NORMAL,
        condition=lambda ctx: ctx.has_gameplay_indicators and ctx.health_percentage < 60,
        action=lambda ctx: ('5', f"Resting to recover (health: {ctx.health_percentage:.1f}%)")
    ))
    
    # LOW PRIORITY: Fallback actions
    
    # Rule: Game not ready - explore anyway
    engine.add_rule(Rule(
        name="Explore (game not ready)",
        priority=Priority.LOW,
        condition=lambda ctx: ctx.has_gameplay_indicators,
        action=lambda ctx: ('o', "Auto-explore")
    ))
    
    # Rule: No gameplay started yet
    engine.add_rule(Rule(
        name="Waiting for gameplay",
        priority=Priority.LOW,
        condition=lambda ctx: not ctx.gameplay_started,
        action=lambda ctx: ('o', "Auto-explore (waiting for gameplay to start)")
    ))
    
    # Rule: Fallback to exploration
    engine.add_rule(Rule(
        name="Fallback exploration",
        priority=Priority.LOW,
        condition=lambda ctx: True,  # Always matches
        action=lambda ctx: ('o', "Auto-explore (fallback)")
    ))
    
    return engine
