"""Tests for DecisionEngine integration (Phase 3b post-migration).

After Phase 3b completion and real game validation, the bot has migrated fully
to DecisionEngine-based decision making. The legacy wrapper and feature flag have
been removed, and the engine is now the sole decision mechanism.

These tests validate the engine-only implementation and its integration with the bot.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.bot import DCSSBot
from src.decision_engine import DecisionContext, Priority, create_default_engine


class TestDecisionEngineIntegration:
    """Test DecisionEngine integration as the primary decision mechanism."""
    
    def test_engine_initialized_in_bot(self):
        """Verify DecisionEngine is initialized in bot."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            assert bot.decision_engine is not None
            assert len(bot.decision_engine.rules) > 0
    
    def test_engine_has_25_rules(self):
        """Verify engine has expected number of rules."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            assert len(bot.decision_engine.rules) >= 25
    
    def test_decide_action_uses_engine_directly(self):
        """Verify _decide_action uses engine directly."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Mock context preparation and engine
            mock_context = MagicMock()
            with patch.object(bot, '_prepare_decision_context', return_value=mock_context) as mock_prepare:
                with patch.object(bot.decision_engine, 'decide', return_value=('o', 'explore')) as mock_decide:
                    result = bot._decide_action("test output")
                    
                    # Should call engine's decide method
                    mock_prepare.assert_called_once_with("test output")
                    mock_decide.assert_called_once_with(mock_context)
                    assert result == 'o'
    
    def test_decide_action_returns_action_from_engine(self):
        """Verify _decide_action returns action from engine."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            bot.gameplay_started = True
            
            mock_context = MagicMock()
            with patch.object(bot, '_prepare_decision_context', return_value=mock_context):
                with patch.object(bot.decision_engine, 'decide', return_value=('\t', 'autofight')):
                    with patch.object(bot, '_return_action', return_value='\t') as mock_return:
                        result = bot._decide_action("test output")
                        
                        mock_return.assert_called_once_with('\t', 'autofight')
                        assert result == '\t'
                        assert bot.engine_decisions_made == 1
    
    def test_engine_decisions_counter_increments(self):
        """Verify engine decisions counter increments."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            assert bot.engine_decisions_made == 0
            
            mock_context = MagicMock()
            with patch.object(bot, '_prepare_decision_context', return_value=mock_context):
                with patch.object(bot.decision_engine, 'decide', return_value=('o', 'explore')):
                    bot._decide_action("test")
                    assert bot.engine_decisions_made == 1
                    
                    bot._decide_action("test")
                    assert bot.engine_decisions_made == 2
    
    def test_engine_fallback_when_no_rule_matches(self):
        """Verify fallback behavior when engine returns no decision."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            mock_context = MagicMock()
            with patch.object(bot, '_prepare_decision_context', return_value=mock_context):
                with patch.object(bot.decision_engine, 'decide', return_value=(None, "")):
                    with patch.object(bot, '_return_action', return_value='o') as mock_return:
                        result = bot._decide_action("test output")
                        
                        # Should fall back to explore
                        mock_return.assert_called_once()
                        call_args = mock_return.call_args[0]
                        assert call_args[0] == 'o'  # Fallback to explore
    
    def test_engine_handles_exceptions_gracefully(self):
        """Verify engine exceptions are handled gracefully."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            mock_context = MagicMock()
            with patch.object(bot, '_prepare_decision_context', return_value=mock_context):
                with patch.object(bot.decision_engine, 'decide', side_effect=RuntimeError("Test error")):
                    with patch.object(bot, '_return_action', return_value='o') as mock_return:
                        result = bot._decide_action("test output")
                        
                        # Should return safe fallback (explore)
                        assert result == 'o'


class TestEngineRuleOrdering:
    """Test that engine rules are properly ordered by priority."""
    
    def test_critical_priority_rules_exist(self):
        """Verify CRITICAL priority rules are present."""
        engine = create_default_engine()
        
        critical_rules = [r for r in engine.rules if r.priority == Priority.CRITICAL]
        assert len(critical_rules) >= 5
    
    def test_all_priority_levels_present(self):
        """Verify all priority levels are represented."""
        engine = create_default_engine()
        
        priorities = {rule.priority for rule in engine.rules}
        required = {Priority.CRITICAL, Priority.URGENT, Priority.HIGH, Priority.NORMAL, Priority.LOW}
        
        assert required.issubset(priorities)


class TestPrepareDecisionContext:
    """Test DecisionContext preparation."""
    
    def test_prepare_decision_context_creates_context(self):
        """Verify _prepare_decision_context creates a valid DecisionContext."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            bot.screen_buffer = MagicMock()
            bot.screen_buffer.get_screen_text.return_value = "Health: 50/50\nTime: 1"
            bot.parser = MagicMock()
            bot.parser.state = MagicMock()
            bot.parser.state.health = 50
            bot.parser.state.max_health = 50
            bot.parser.state.experience_level = 5
            bot.parser.state.dungeon_level = 1
            
            context = bot._prepare_decision_context("test output")
            
            assert isinstance(context, DecisionContext)
            assert context.health == 50
            assert context.max_health == 50
            assert context.level == 5
    
    def test_context_health_percentage_property(self):
        """Verify DecisionContext.health_percentage property works correctly."""
        ctx = DecisionContext(
            output="test",
            health=50,
            max_health=100,
            level=5,
            dungeon_level=1,
            enemy_detected=False,
            enemy_name="",
            items_on_ground=False,
            in_shop=False,
            in_inventory_screen=False,
            in_item_pickup_menu=False,
            in_menu=False,
            equip_slot_pending=False,
            quaff_slot_pending=False,
            has_level_up=False,
            has_more_prompt=False,
            attribute_increase_prompt=False,
            save_game_prompt=False,
            last_action_sent="",
            last_level_up_processed=0,
            last_attribute_increase_level=0,
            last_equipment_check=0,
            last_inventory_refresh=0,
            move_count=0,
            has_gameplay_indicators=True,
            gameplay_started=True,
            goto_state=None,
            goto_target_level=0,
        )
        
        assert ctx.health_percentage == 50.0


class TestEngineDecisionQuality:
    """Test that engine makes high-quality decisions."""
    
    def test_autofight_with_high_health(self):
        """Verify autofight is chosen with high health."""
        engine = create_default_engine()
        
        ctx = DecisionContext(
            output="test",
            health=45,
            max_health=50,  # 90% health
            level=5,
            dungeon_level=1,
            enemy_detected=True,
            enemy_name="goblin",
            items_on_ground=False,
            in_shop=False,
            in_inventory_screen=False,
            in_item_pickup_menu=False,
            in_menu=False,
            equip_slot_pending=False,
            quaff_slot_pending=False,
            has_level_up=False,
            has_more_prompt=False,
            attribute_increase_prompt=False,
            save_game_prompt=False,
            last_action_sent="",
            last_level_up_processed=0,
            last_attribute_increase_level=0,
            last_equipment_check=0,
            last_inventory_refresh=0,
            move_count=0,
            has_gameplay_indicators=True,
            gameplay_started=True,
            goto_state=None,
            goto_target_level=0,
        )
        
        action, reason = engine.decide(ctx)
        assert action == '\t'
    
    def test_explore_with_good_health(self):
        """Verify exploration is chosen with good health and no enemy."""
        engine = create_default_engine()
        
        ctx = DecisionContext(
            output="test",
            health=40,
            max_health=50,  # 80% health
            level=5,
            dungeon_level=1,
            enemy_detected=False,
            enemy_name="",
            items_on_ground=False,
            in_shop=False,
            in_inventory_screen=False,
            in_item_pickup_menu=False,
            in_menu=False,
            equip_slot_pending=False,
            quaff_slot_pending=False,
            has_level_up=False,
            has_more_prompt=False,
            attribute_increase_prompt=False,
            save_game_prompt=False,
            last_action_sent="",
            last_level_up_processed=0,
            last_attribute_increase_level=0,
            last_equipment_check=0,
            last_inventory_refresh=0,
            move_count=0,
            has_gameplay_indicators=True,
            gameplay_started=True,
            goto_state=None,
            goto_target_level=0,
        )
        
        action, reason = engine.decide(ctx)
        assert action == 'o'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
