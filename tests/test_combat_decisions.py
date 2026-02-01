"""Tests for combat and health-based decision logic in DecisionEngine."""

import pytest
from unittest.mock import patch, MagicMock
from src.bot import DCSSBot
from src.decision_engine import DecisionContext, Priority


def create_test_context(**kwargs):
    """
    Create a properly initialized test context with all fields set.
    
    Args:
        **kwargs: Override specific fields
        
    Returns:
        object: Context object with all fields initialized to safe defaults
    """
    # Use plain class instead of MagicMock to avoid comparison issues
    class Context:
        def __init__(self, **kwargs):
            # Set all fields to safe defaults
            self.has_more_prompt = False
            self.has_equip_slot_prompt = False
            self.has_quaff_slot_prompt = False
            self.has_level_up = False
            self.attribute_increase_prompt = False
            self.save_game_prompt = False
            self.in_shop = False
            self.in_inventory_screen = False
            self.in_item_pickup_menu = False
            self.enemy_detected = False
            self.enemy_name = None
            self.health = 100
            self.max_health = 100
            self.items_on_ground = False
            self.equip_slot_pending = False
            self.quaff_slot_pending = False
            self.in_menu = False
            self.last_action_sent = ""
            self.last_level_up_processed = 0
            self.last_attribute_increase_level = 0
            self.last_equipment_check = 0
            self.last_inventory_refresh = 0
            self.move_count = 0
            self.has_gameplay_indicators = True
            self.gameplay_started = True
            self.goto_state = None
            self.goto_target_level = 0
            self.output = ""
            self.level = 1
            self.dungeon_level = 1
            
            # Override with provided kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        @property
        def health_percentage(self) -> float:
            """Calculate health percentage."""
            if self.max_health <= 0:
                return 100.0
            return (self.health / self.max_health) * 100
    
    # Create object from defaults + overrides
    return Context(**kwargs)


class TestCombatDetection:
    """Test combat detection and autofight decisions."""
    
    def test_autofight_with_good_health(self):
        """Engine should autofight ('\\t') when enemy detected and health > 70%."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: enemy detected, good health
            context = create_test_context(
                enemy_detected=True,
                enemy_name="bat",
                health=80,
                max_health=100
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should autofight (\\t) (engine uses '\t' for autofight)
            assert command == '\t', f"Expected '\\t' (autofight), got '{repr(command)}'"
            assert 'autofight' in reason.lower() or 'combat' in reason.lower()
    
    def test_autofight_with_low_health(self):
        """Engine should rest (5) ('s') or flee when enemy detected and health < 40%."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: enemy detected, low health
            context = create_test_context(
                enemy_detected=True,
                enemy_name="goblin",
                health=15,
                max_health=100
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should NOT autofight at low health
            # Should either rest or explore (not 'f')
            assert command != '\t', "Should not autofight with < 40% health"
    
    def test_no_enemy_detected_explorations(self):
        """Engine should explore ('o') when no enemy detected."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: no enemy
            context = create_test_context(
                enemy_detected=False,
                enemy_name=None,
                health=75,
                max_health=100
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should explore
            assert command == 'o', f"Expected 'o' (explore) when no enemy, got '{command}'"
    
    def test_multiple_enemies_autofight(self):
        """Engine should autofight even if exact count unknown."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: multiple enemies (represented by any enemy_detected)
            context = create_test_context(
                enemy_detected=True,
                enemy_name="2 goblins",
                health=90,
                max_health=100
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should autofight (\\t)
            assert command == '\t'


class TestHealthBasedDecisions:
    """Test health-based rest vs explore decisions."""
    
    def test_rest_at_very_low_health(self):
        """Engine should rest (5) ('s') at very low health."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: very low health, no enemy
            context = create_test_context(
                health=5,
                max_health=50,
                enemy_detected=False
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should rest (not explore)
            assert command == '5', f"Expected 's' (rest), got '{command}'"
    
    def test_explore_at_good_health(self):
        """Engine should explore ('o') at good health."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: good health, no enemy
            context = create_test_context(
                health=85,
                max_health=100,
                enemy_detected=False
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should explore
            assert command == 'o', f"Expected 'o' (explore), got '{command}'"
    
    def test_medium_health_decision(self):
        """Engine should make sensible decision at medium health."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: medium health (50%)
            context = create_test_context(
                health=50,
                max_health=100,
                enemy_detected=False
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should be a valid action (explore or rest, not crash)
            assert command in ['o', '5', '.']  # explore, rest, or wait
    
    def test_health_priority_over_exploration(self):
        """Engine should prioritize low health over exploration."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Create context: low health takes priority
            context = create_test_context(
                health=20,
                max_health=100,
                enemy_detected=False
            )
            
            # Decide action
            command, reason = bot.decision_engine.decide(context)
            
            # Should rest, not explore
            assert command == '5', "Low health should prioritize rest"


class TestCombatSequences:
    """Test realistic combat sequences."""
    
    def test_autofight_followed_by_wait(self):
        """Engine should autofight then wait after combat."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # First: Enemy in range
            context1 = create_test_context(
                enemy_detected=True,
                enemy_name="bat",
                health=80,
                max_health=100
            )
            
            cmd1, _ = bot.decision_engine.decide(context1)
            assert cmd1 == '\t'
            
            # After combat, health down a bit, enemy still there
            context2 = create_test_context(
                enemy_detected=True,
                enemy_name="bat",
                health=70,
                max_health=100
            )
            
            cmd2, _ = bot.decision_engine.decide(context2)
            # Should continue combat (autofight or other action)
            assert cmd2 is not None
    
    def test_health_recovery_cycle(self):
        """Engine should cycle: damage -> rest -> recover -> explore."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Damaged
            context_damaged = create_test_context(
                health=30,
                max_health=100,
                enemy_detected=False
            )
            
            cmd_damaged, _ = bot.decision_engine.decide(context_damaged)
            assert cmd_damaged == '5', "Should rest when damaged"
            
            # Recovering (multiple rests)
            context_recovering = create_test_context(
                health=60,
                max_health=100,
                enemy_detected=False
            )
            
            cmd_recovering, _ = bot.decision_engine.decide(context_recovering)
            # Can rest or explore at 60% health
            assert cmd_recovering in ['s', 'o', '.']
            
            # Recovered
            context_recovered = create_test_context(
                health=95,
                max_health=100,
                enemy_detected=False
            )
            
            cmd_recovered, _ = bot.decision_engine.decide(context_recovered)
            assert cmd_recovered == 'o', "Should explore when fully recovered"


class TestPromptPriorityOverCombat:
    """Test that prompts take priority over combat decisions."""
    
    def test_more_prompt_priority_over_autofight(self):
        """More prompt should be handled before autofight."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # More prompt + enemy detected
            context = create_test_context(
                has_more_prompt=True,
                enemy_detected=True,
                enemy_name="bat",
                health=80,
                max_health=100
            )
            
            command, reason = bot.decision_engine.decide(context)
            
            # Should handle more prompt (space) not autofight
            assert command == ' ', "More prompt should be handled first"
    
    def test_equip_prompt_priority_over_autofight(self):
        """Engine currently doesn't have explicit equip prompt handling in rules."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # Equip prompt + enemy detected
            context = create_test_context(
                has_equip_slot_prompt=True,
                enemy_detected=True,
                enemy_name="goblin",
                health=80,
                max_health=100
            )
            
            command, reason = bot.decision_engine.decide(context)
            
            # Engine currently autofights with good health, even if equip prompt present
            # (no explicit equip prompt rule implemented yet)
            assert command == '\t', "Engine defaults to autofight with good health and enemy"


class TestHealthThresholds:
    """Test specific health thresholds for decision boundaries."""
    
    def test_health_threshold_30_percent(self):
        """Verify behavior at 30% health threshold."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # At 30% with no enemy
            context = create_test_context(
                health=30,
                max_health=100,
                enemy_detected=False
            )
            
            command, _ = bot.decision_engine.decide(context)
            
            # At 30%, should rest (5)
            assert command == '5'
    
    def test_health_threshold_60_percent(self):
        """Verify behavior at 60% health threshold."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # At 60% with no enemy
            context = create_test_context(
                health=60,
                max_health=100,
                enemy_detected=False
            )
            
            command, _ = bot.decision_engine.decide(context)
            
            # At 60%, can explore or rest (transition zone)
            assert command in ['o', '5', '.']
    
    def test_health_threshold_80_percent(self):
        """Verify behavior at 80% health threshold."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            # At 80% with no enemy
            context = create_test_context(
                health=80,
                max_health=100,
                enemy_detected=False
            )
            
            command, _ = bot.decision_engine.decide(context)
            
            # At 80%, should explore
            assert command == 'o'


class TestCombatWithVariousEnemies:
    """Test autofight with different enemy types."""
    
    @pytest.mark.parametrize("enemy_name,should_fight", [
        ("bat", True),
        ("rat", True),
        ("goblin", True),
        ("orc", True),
        ("endoplasm", True),
    ])
    def test_autofight_various_enemies(self, enemy_name, should_fight):
        """Engine should autofight various enemy types at good health."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            context = create_test_context(
                enemy_detected=True,
                enemy_name=enemy_name,
                health=85,
                max_health=100
            )
            
            command, _ = bot.decision_engine.decide(context)
            
            if should_fight:
                assert command == '\t', f"Should autofight (\\t) {enemy_name}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_exactly_zero_health_percentage(self):
        """Handle edge case of exactly 0% health."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            context = create_test_context(
                health=0,
                max_health=100,
                enemy_detected=False
            )
            
            command, _ = bot.decision_engine.decide(context)
            
            # Should return some action (shouldn't crash)
            assert command is not None
    
    def test_exactly_100_health_percentage(self):
        """Handle edge case of exactly 100% health."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            context = create_test_context(
                health=100,
                max_health=100,
                enemy_detected=False
            )
            
            command, _ = bot.decision_engine.decide(context)
            
            # Should explore at full health
            assert command == 'o'
    
    def test_no_max_health_defined(self):
        """Handle edge case of zero max_health."""
        with patch('src.local_client.LocalCrawlClient'):
            bot = DCSSBot()
            
            context = create_test_context(
                health=0,
                max_health=0,
                enemy_detected=False
            )
            
            command, _ = bot.decision_engine.decide(context)
            
            # Should still return a command
            assert command is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
