"""Integration tests for DecisionEngine with real game scenarios."""

import pytest
from src.decision_engine import DecisionEngine, DecisionContext, create_default_engine


class TestDecisionEngineIntegration:
    """Integration tests using real game scenarios."""
    
    def test_menu_prompt_priority_over_combat(self):
        """Test that menu prompts take priority over combat."""
        engine = create_default_engine()
        
        # Scenario: Both menu prompt AND enemy detected
        # Menu prompts should take priority (CRITICAL vs NORMAL)
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=True, enemy_name="goblin",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=True,  # ← Menu prompt (CRITICAL priority)
            quaff_slot_pending=False, has_level_up=False, has_more_prompt=False,
            attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        # Should be empty (handled by bot with stored slot), not combat
        # Engine returns empty string for pending prompts
        assert "equip" in reason.lower() or command == ""
    
    def test_shop_exit_before_exploration(self):
        """Test that shop exit happens before exploration."""
        engine = create_default_engine()
        
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=True,  # ← Shop detected
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        assert command == '\x1b'  # Escape to exit shop
        assert 'shop' in reason.lower()
    
    def test_level_up_handling_sequence(self):
        """Test that level-up with prompts is handled correctly."""
        engine = create_default_engine()
        
        # Level-up with --more-- prompt
        # Note: --more-- takes CRITICAL priority, so it's handled first
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=2, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False,
            has_level_up=True, has_more_prompt=True,  # Both set
            attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=1,  # New level (2 > 1)
            last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        # More prompt takes CRITICAL priority over level-up (which is URGENT)
        # So it should dismiss the more prompt first
        assert command == ' '  # Space to dismiss more
        assert 'more' in reason.lower()
    
    def test_combat_sequence_scenario(self):
        """Test realistic combat sequence."""
        engine = create_default_engine()
        
        # Enemy detected with good health
        ctx_combat = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=True, enemy_name="bat",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        # Should use autofight
        cmd1, reason1 = engine.decide(ctx_combat)
        assert cmd1 == '\t'
        assert 'autofight' in reason1.lower()
        
        # After combat, wait
        ctx_wait = DecisionContext(
            output="", health=75, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent='\t',  # ← Just sent autofight
            last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        cmd2, reason2 = engine.decide(ctx_wait)
        assert cmd2 == '.'  # Wait after autofight
        
        # Recovery phase - low health
        ctx_recover = DecisionContext(
            output="", health=40, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent=".", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        cmd3, reason3 = engine.decide(ctx_recover)
        assert cmd3 == '5'  # Rest to recover
        assert 'recover' in reason3.lower()
    
    def test_exploration_health_management(self):
        """Test health-based exploration decisions."""
        engine = create_default_engine()
        
        # Good health - explore
        ctx_good = DecisionContext(
            output="", health=75, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        cmd1, reason1 = engine.decide(ctx_good)
        assert cmd1 == 'o'  # Explore
        
        # Exactly 60% health - should still explore (threshold is >=60%)
        ctx_threshold = DecisionContext(
            output="", health=60, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        cmd2, reason2 = engine.decide(ctx_threshold)
        assert cmd2 == 'o'  # Still explore at boundary
        
        # Below 60% - rest
        ctx_low = DecisionContext(
            output="", health=50, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        cmd3, reason3 = engine.decide(ctx_low)
        assert cmd3 == '5'  # Rest
        assert 'recover' in reason3.lower()
    
    def test_more_prompt_priority(self):
        """Test that --more-- prompts are dismissed at CRITICAL priority."""
        engine = create_default_engine()
        
        # More prompt should take priority over exploration
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=True,  # Items available
            in_shop=False, in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=True,  # ← More prompt (CRITICAL)
            attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        assert command == ' '  # Dismiss more prompt
        assert 'more' in reason.lower()
    
    def test_save_game_prompt_rejection(self):
        """Test that save game prompts are rejected."""
        engine = create_default_engine()
        
        ctx = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=True, enemy_name="goblin", enemy_direction=None,  # Enemy present (would normally fight)
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False,
            save_game_prompt=True,  # ← Save game prompt (CRITICAL - takes priority)
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        assert command == 'n'  # Reject save game
        assert 'save' in reason.lower()
    
    def test_goto_sequence(self):
        """Test level descent goto sequence."""
        engine = create_default_engine()
        
        # Awaiting location type
        ctx1 = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True,
            goto_state='awaiting_location_type', goto_target_level=2
        )
        
        cmd1, reason1 = engine.decide(ctx1)
        assert cmd1 == 'D'  # Dungeon
        
        # Awaiting level number
        ctx2 = DecisionContext(
            output="", health=80, max_health=100, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True,
            goto_state='awaiting_level_number', goto_target_level=5
        )
        
        cmd2, reason2 = engine.decide(ctx2)
        assert cmd2 == '5'  # Level 5
        assert '5' in reason2


class TestDecisionEngineWithRealGameStates:
    """Test with scenarios extracted from real game sessions."""
    
    def test_early_game_startup(self):
        """Test decision engine during early game startup."""
        engine = create_default_engine()
        
        # No enemies yet, game just started
        ctx = DecisionContext(
            output="", health=9, max_health=9, level=1, dungeon_level=1,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=0,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        assert command == 'o'  # Auto-explore
    
    def test_low_health_emergency(self):
        """Test decision under critical health (near death)."""
        engine = create_default_engine()
        
        ctx = DecisionContext(
            output="", health=2, max_health=20, level=3, dungeon_level=2,
            enemy_detected=False, enemy_name="",
            enemy_direction=None,
            items_on_ground=False, in_shop=False,
            in_inventory_screen=False, in_item_pickup_menu=False, in_menu=False,
            equip_slot_pending=False, quaff_slot_pending=False, has_level_up=False,
            has_more_prompt=False, attribute_increase_prompt=False, save_game_prompt=False,
            last_action_sent="", last_level_up_processed=0, last_attribute_increase_level=0,
            last_equipment_check=0, last_inventory_refresh=0, move_count=50,
            has_gameplay_indicators=True, gameplay_started=True, goto_state=None, goto_target_level=0
        )
        
        command, reason = engine.decide(ctx)
        assert command == '5'  # Emergency rest
        assert '10' in reason  # Health percentage in reason
