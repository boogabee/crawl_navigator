"""Tests for DecisionEngine."""

import pytest
from src.decision_engine import (
    DecisionEngine, Rule, Priority, DecisionContext,
    create_default_engine
)


class TestRule:
    """Test individual Rule creation and evaluation."""
    
    def test_rule_creation(self):
        """Test that rules can be created with condition and action."""
        rule = Rule(
            name="test_rule",
            priority=Priority.HIGH,
            condition=lambda ctx: ctx.health > 50,
            action=lambda ctx: ('o', 'exploring')
        )
        assert rule.name == "test_rule"
        assert rule.priority == Priority.HIGH
    
    def test_rule_condition_true(self):
        """Test rule condition that evaluates to true."""
        rule = Rule(
            name="health_check",
            priority=Priority.NORMAL,
            condition=lambda ctx: ctx.health > 50,
            action=lambda ctx: ('o', 'exploring')
        )
        ctx = DecisionContext(
            output="", health=75, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        assert rule.condition(ctx) is True
        command, reason = rule.action(ctx)
        assert command == 'o'
    
    def test_rule_condition_false(self):
        """Test rule condition that evaluates to false."""
        rule = Rule(
            name="health_check",
            priority=Priority.NORMAL,
            condition=lambda ctx: ctx.health > 50,
            action=lambda ctx: ('o', 'exploring')
        )
        ctx = DecisionContext(
            output="", health=25, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        assert rule.condition(ctx) is False


class TestDecisionContext:
    """Test DecisionContext and its properties."""
    
    def test_health_percentage_calculation(self):
        """Test health percentage property."""
        ctx = DecisionContext(
            output="", health=50, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        assert ctx.health_percentage == 50.0
    
    def test_health_percentage_zero_max_health(self):
        """Test health percentage with zero max health."""
        ctx = DecisionContext(
            output="", health=0, max_health=0, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        assert ctx.health_percentage == 100.0


class TestDecisionEngine:
    """Test DecisionEngine rule evaluation."""
    
    def test_engine_creation(self):
        """Test that engine can be created and has no initial rules."""
        engine = DecisionEngine()
        assert len(engine.rules) == 0
    
    def test_add_rule(self):
        """Test adding rules to engine."""
        engine = DecisionEngine()
        rule = Rule(
            name="test",
            priority=Priority.NORMAL,
            condition=lambda ctx: True,
            action=lambda ctx: ('o', 'test')
        )
        result = engine.add_rule(rule)
        assert result is engine  # Chainable
        assert len(engine.rules) == 1
    
    def test_rule_chaining(self):
        """Test that add_rule returns self for chaining."""
        engine = DecisionEngine()
        rule1 = Rule("r1", Priority.CRITICAL, lambda ctx: False, lambda ctx: ('a', 'a'))
        rule2 = Rule("r2", Priority.NORMAL, lambda ctx: True, lambda ctx: ('b', 'b'))
        
        engine.add_rule(rule1).add_rule(rule2)
        assert len(engine.rules) == 2
    
    def test_decide_first_matching_rule(self):
        """Test that decide returns first matching rule."""
        engine = DecisionEngine()
        engine.add_rule(Rule("r1", Priority.HIGH, lambda ctx: ctx.health > 50, lambda ctx: ('a', 'healthy')))
        engine.add_rule(Rule("r2", Priority.LOW, lambda ctx: ctx.health <= 50, lambda ctx: ('b', 'damaged')))
        
        ctx = DecisionContext(
            output="", health=75, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        assert command == 'a'
        assert reason == 'healthy'
    
    def test_decide_priority_order(self):
        """Test that rules are evaluated in priority order."""
        engine = DecisionEngine()
        # Add rules in reverse priority order
        engine.add_rule(Rule("low", Priority.LOW, lambda ctx: True, lambda ctx: ('low', 'low')))
        engine.add_rule(Rule("critical", Priority.CRITICAL, lambda ctx: True, lambda ctx: ('critical', 'critical')))
        engine.add_rule(Rule("normal", Priority.NORMAL, lambda ctx: True, lambda ctx: ('normal', 'normal')))
        
        ctx = DecisionContext(
            output="", health=50, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        # CRITICAL should match first
        assert command == 'critical'
    
    def test_decide_no_matching_rules(self):
        """Test that decide handles no matching rules gracefully."""
        engine = DecisionEngine()
        engine.add_rule(Rule("r1", Priority.CRITICAL, lambda ctx: False, lambda ctx: ('a', 'a')))
        
        ctx = DecisionContext(
            output="", health=50, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        assert command is None


class TestDefaultEngine:
    """Test the default engine configuration."""
    
    def test_create_default_engine(self):
        """Test that default engine can be created."""
        engine = create_default_engine()
        assert len(engine.rules) > 0
    
    def test_combat_with_good_health(self):
        """Test that combat rule triggers with good health."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=True, enemy_name="goblin", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        command, reason = engine.decide(ctx)
        assert command == '\t'  # Autofight
        assert 'Autofight' in reason
    
    def test_combat_with_low_health(self):
        """Test that combat uses movement toward enemy with low health."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=40, max_health=100, level=1, dungeon_level=1,
            enemy_detected=True, enemy_name="bat", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        command, reason = engine.decide(ctx)
        # When health is low, DCSS disables autofight, so bot must move toward enemy
        # Engine returns a movement command ('l' = right, will need direction calculation later)
        assert command == 'l'  # Move right as default direction
        assert 'low health' in reason.lower()
        assert 'bat' in reason.lower()
    
    def test_exploration_with_good_health(self):
        """Test exploration rule triggers with good health and no enemies."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        command, reason = engine.decide(ctx)
        assert command == 'o'  # Auto-explore
    
    def test_rest_with_low_health(self):
        """Test that bot rests with low health."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=40, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        command, reason = engine.decide(ctx)
        assert command == '5'  # Rest
    
    def test_shop_exit(self):
        """Test that bot exits shop immediately."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=True,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        command, reason = engine.decide(ctx)
        assert command == '\x1b'  # Escape
    
    def test_more_prompt_dismissed(self):
        """Test that --more-- prompt is dismissed."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=True, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        command, reason = engine.decide(ctx)
        assert command == ' '  # Space to dismiss
    
    def test_attribute_increase(self):
        """Test that attribute increase prompt is handled."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=2, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=True, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=1,  # New level
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        command, reason = engine.decide(ctx)
        assert command == 'S'  # Strength increase
    
    def test_goto_location_type(self):
        """Test goto location type response."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state='awaiting_location_type', goto_target_level=2
        )
        command, reason = engine.decide(ctx)
        assert command == 'D'  # Dungeon
    
    def test_goto_level_number(self):
        """Test goto level number response."""
        engine = create_default_engine()
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="", items_on_ground=False, in_shop=False,
            enemy_direction=None,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state='awaiting_level_number', goto_target_level=5
        )
        command, reason = engine.decide(ctx)
        assert command == '5'


class TestPriority:
    """Test Priority enum values."""
    
    def test_priority_values(self):
        """Test that priorities have correct numeric values."""
        assert Priority.CRITICAL.value < Priority.URGENT.value
        assert Priority.URGENT.value < Priority.HIGH.value
        assert Priority.HIGH.value < Priority.NORMAL.value
        assert Priority.NORMAL.value < Priority.LOW.value
