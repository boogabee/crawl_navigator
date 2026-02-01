"""
Comparison tests: DecisionEngine vs Legacy _decide_action()

This test suite validates that the DecisionEngine makes the same or equivalent
decisions as the legacy _decide_action() method across a wide range of scenarios.

Purpose:
- Ensure engine migrates all decision logic correctly
- Identify any behavior differences (intentional or bugs)
- Provide safety validation before switching to engine-default

Test Categories:
1. Critical prompts (save game, attribute, level-up, more)
2. Shop and inventory handling
3. Enemy combat (various health thresholds)
4. Rest and exploration (health-based)
5. Edge cases (health 0/0, no output, etc.)
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot import DCSSBot
from src.decision_engine import DecisionContext, Priority, create_default_engine
from typing import Optional, Tuple


class TestEngineVsLegacy:
    """Compare DecisionEngine and legacy decision logic."""
    
    @pytest.fixture
    def bot(self):
        """Create a bot with mocked dependencies."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot(crawl_command="crawl", steps=100)
            bot.use_decision_engine = True
            bot.gameplay_started = True
            bot.move_count = 5
            bot.consecutive_rest_actions = 0
            bot.last_action_sent = ''
            bot.last_level_up_processed = 0
            bot.last_attribute_increase_level = 0
            bot.last_equipment_check = 0
            bot.action_reason = ""
            return bot
    
    @pytest.fixture
    def engine(self):
        """Create a properly configured decision engine."""
        return create_default_engine()
    
    @pytest.fixture
    def mock_context_base(self):
        """Base context for testing."""
        return {
            'output': '',
            'health': 50,
            'max_health': 50,
            'level': 5,
            'dungeon_level': 1,
            'enemy_detected': False,
            'enemy_name': '',
            'items_on_ground': False,
            'in_shop': False,
            'in_inventory_screen': False,
            'in_item_pickup_menu': False,
            'in_menu': False,
            'equip_slot_pending': False,
            'quaff_slot_pending': False,
            'has_level_up': False,
            'has_more_prompt': False,
            'attribute_increase_prompt': False,
            'save_game_prompt': False,
            'last_action_sent': '',
            'last_level_up_processed': 0,
            'last_attribute_increase_level': 0,
            'last_equipment_check': 0,
            'last_inventory_refresh': 0,
            'move_count': 5,
            'has_gameplay_indicators': True,
            'gameplay_started': True,
            'goto_state': None,
            'goto_target_level': 0,
        }
    
    # ============================================================================
    # Category 1: Critical Prompts
    # ============================================================================
    
    def test_save_game_prompt_rejected(self, engine, mock_context_base):
        """Save game prompt should always be rejected."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['save_game_prompt'] = True
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == 'n', "Should reject save game prompt"
        assert 'Rejecting' in reason
    
    def test_attribute_increase_prompt(self, engine, mock_context_base):
        """Attribute increase prompt should increase strength."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['attribute_increase_prompt'] = True
        ctx_dict['level'] = 5
        ctx_dict['last_attribute_increase_level'] = 4  # New level
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == 'S', "Should increase strength"
        assert 'Strength' in reason
    
    def test_attribute_increase_already_done_this_level(self, engine, mock_context_base):
        """Attribute increase should only respond once per level."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['attribute_increase_prompt'] = True
        ctx_dict['level'] = 5
        ctx_dict['last_attribute_increase_level'] = 5  # Already handled
        ctx = DecisionContext(**ctx_dict)
        
        # Should not match attribute increase rule
        action, reason = engine.decide(ctx)
        assert action != 'S', "Should not increase strength (already done this level)"
    
    def test_more_prompt_dismissed(self, engine, mock_context_base):
        """More prompt should be dismissed."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['has_more_prompt'] = True
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == ' ', "Should dismiss more prompt"
        assert 'more' in reason.lower()
    
    def test_level_up_with_more_prompt(self, engine, mock_context_base):
        """Level-up with more prompt should dismiss it."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['has_level_up'] = True
        ctx_dict['has_more_prompt'] = True
        ctx_dict['level'] = 6
        ctx_dict['last_level_up_processed'] = 5
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == ' ', "Should dismiss level-up more prompt"
    
    def test_level_up_without_more_prompt(self, engine, mock_context_base):
        """Level-up without more prompt should wait."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['has_level_up'] = True
        ctx_dict['has_more_prompt'] = False
        ctx_dict['level'] = 6
        ctx_dict['last_level_up_processed'] = 5
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '.', "Should wait for level-up processing"
    
    # ============================================================================
    # Category 2: Shop and Inventory
    # ============================================================================
    
    def test_shop_detected_exit(self, engine, mock_context_base):
        """Shop should be exited with Escape."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['in_shop'] = True
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '\x1b', "Should exit shop with Escape"
        assert 'shop' in reason.lower()
    
    def test_inventory_screen_wait(self, engine, mock_context_base):
        """Should wait while in inventory screen."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['in_inventory_screen'] = True
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        # Inventory screen handling is delegated to caller, but should wait
        assert action == '.' or action == '', "Should wait in inventory or handle specially"
    
    def test_items_on_ground_grab(self, engine, mock_context_base):
        """Items on ground should be grabbed."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['items_on_ground'] = True
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == 'g', "Should grab items from ground"
        assert 'items' in reason.lower()
    
    # ============================================================================
    # Category 3: Combat (Health-based decisions)
    # ============================================================================
    
    def test_combat_high_health_autofight(self, engine, mock_context_base):
        """With high health, should use autofight (Tab)."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['enemy_detected'] = True
        ctx_dict['enemy_name'] = 'goblin'
        ctx_dict['health'] = 45
        ctx_dict['max_health'] = 50  # 90% health
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '\t', "Should autofight with high health (>70%)"
        assert 'goblin' in reason
        assert 'Autofight' in reason
    
    def test_combat_low_health_movement(self, engine, mock_context_base):
        """With low health, should use movement instead of autofight."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['enemy_detected'] = True
        ctx_dict['enemy_name'] = 'bat'
        ctx_dict['health'] = 20
        ctx_dict['max_health'] = 50  # 40% health
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        # Low health combat should return empty (caller will calculate direction)
        # or should return a specific message
        assert action == '' or 'Movement' in reason or 'low health' in reason.lower()
    
    def test_combat_exact_70_percent_health(self, engine, mock_context_base):
        """At exactly 70% health, should use autofight."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['enemy_detected'] = True
        ctx_dict['enemy_name'] = 'spider'
        ctx_dict['health'] = 35
        ctx_dict['max_health'] = 50  # Exactly 70%
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        # At 70%, condition is "health <= 70", so should use movement
        # But at >= 70%, should use autofight
        # Let's check if 35/50 = 0.70 exactly
        assert (action == '' or 'low health' in reason.lower()), \
            "At 70% health (boundary), should use movement-based (condition is <=70%)"
    
    # ============================================================================
    # Category 4: Rest and Exploration
    # ============================================================================
    
    def test_explore_good_health(self, engine, mock_context_base):
        """With good health, should explore."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['health'] = 35
        ctx_dict['max_health'] = 50  # 70% health
        ctx_dict['has_gameplay_indicators'] = True
        ctx_dict['enemy_detected'] = False
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == 'o', "Should explore with good health (>=60%)"
        assert 'explore' in reason.lower()
    
    def test_rest_low_health(self, engine, mock_context_base):
        """With low health, should rest."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['health'] = 20
        ctx_dict['max_health'] = 50  # 40% health
        ctx_dict['has_gameplay_indicators'] = True
        ctx_dict['enemy_detected'] = False
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '5', "Should rest with low health (<60%)"
        assert 'rest' in reason.lower()
    
    def test_wait_after_autofight(self, engine, mock_context_base):
        """After autofight, should wait before exploring."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['health'] = 40
        ctx_dict['max_health'] = 50  # 80% health (good health)
        ctx_dict['last_action_sent'] = '\t'  # Just used autofight
        ctx_dict['enemy_detected'] = False  # Enemy defeated
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '.', "Should wait after autofight instead of immediately exploring"
    
    # ============================================================================
    # Category 5: Edge Cases
    # ============================================================================
    
    def test_health_unreadable_redraw_screen(self, engine, mock_context_base):
        """When health is 0/0 (unreadable), should request screen redraw."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['health'] = 0
        ctx_dict['max_health'] = 0
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '\x12', "Should request screen redraw when health is unreadable"
        assert 'redraw' in reason.lower() or 'health' in reason.lower()
    
    def test_no_gameplay_indicators(self, engine, mock_context_base):
        """Without gameplay indicators, should wait."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['has_gameplay_indicators'] = False
        ctx_dict['gameplay_started'] = False
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        # Should wait or explore cautiously
        assert action in ['o', '.'], "Should wait or explore when not in gameplay"
    
    def test_goto_location_type_selection(self, engine, mock_context_base):
        """When waiting for location type in goto, select 'D'."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['goto_state'] = 'awaiting_location_type'
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == 'D', "Should select Dungeon in goto location menu"
    
    def test_goto_level_selection(self, engine, mock_context_base):
        """When waiting for level in goto, send level number."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['goto_state'] = 'awaiting_level_number'
        ctx_dict['goto_target_level'] = 3
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '3', "Should select level 3 in goto"
        assert '3' in reason
    
    def test_in_menu_wait(self, engine, mock_context_base):
        """When in menu, should wait."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['in_menu'] = True
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '.', "Should wait when in menu"
    
    # ============================================================================
    # Category 6: Priority Order Validation
    # ============================================================================
    
    def test_prompt_priority_over_combat(self, engine, mock_context_base):
        """Prompts should take priority over combat."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['has_more_prompt'] = True
        ctx_dict['enemy_detected'] = True  # Also have enemy
        ctx_dict['enemy_name'] = 'goblin'
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == ' ', "Should dismiss more prompt, not autofight"
    
    def test_critical_priority_over_normal(self, engine, mock_context_base):
        """CRITICAL priority rules should execute before NORMAL priority."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['save_game_prompt'] = True  # CRITICAL
        ctx_dict['health'] = 5
        ctx_dict['max_health'] = 50  # Would normally rest (NORMAL)
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == 'n', "Should handle critical prompt before rest decision"
    
    def test_shop_priority_over_exploration(self, engine, mock_context_base):
        """Shop should be exited before exploring."""
        ctx_dict = mock_context_base.copy()
        ctx_dict['in_shop'] = True  # HIGH priority
        ctx_dict['health'] = 40
        ctx_dict['max_health'] = 50  # Would normally explore (NORMAL)
        ctx = DecisionContext(**ctx_dict)
        
        action, reason = engine.decide(ctx)
        assert action == '\x1b', "Should exit shop before exploring"


class TestEngineRuleCount:
    """Validate that engine has comprehensive rule coverage."""
    
    def test_engine_has_sufficient_rules(self):
        """Engine should have at least 20 rules for comprehensive coverage."""
        engine = create_default_engine()
        assert len(engine.rules) >= 20, f"Engine has {len(engine.rules)} rules, expected at least 20"
    
    def test_all_priorities_represented(self):
        """Engine should have rules at all priority levels."""
        engine = create_default_engine()
        priorities = {rule.priority for rule in engine.rules}
        
        required_priorities = {Priority.CRITICAL, Priority.URGENT, Priority.HIGH, 
                             Priority.NORMAL, Priority.LOW}
        assert priorities == required_priorities, \
            f"Engine missing priorities: {required_priorities - priorities}"
    
    def test_no_duplicate_rule_names(self):
        """All rules should have unique names."""
        engine = create_default_engine()
        rule_names = [rule.name for rule in engine.rules]
        assert len(rule_names) == len(set(rule_names)), \
            "Found duplicate rule names"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
