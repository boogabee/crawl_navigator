"""Tests using actual game screen output for validation."""

import pytest
from bot import DCSSBot


class TestEnemyDetectionRealScreens:
    """Test enemy detection against real DCSS game screens."""

    def test_single_enemy_extraction(self, game_screen_single_enemy):
        """Test extraction of enemy name from single enemy screen (hobgoblin)."""
        bot = DCSSBot()
        
        # Should extract hobgoblin from the TUI monsters list
        enemies = bot._extract_all_enemies_from_tui(game_screen_single_enemy)
        
        assert len(enemies) > 0, "Should find enemies in TUI section"
        assert "hobgoblin" in enemies, f"Expected 'hobgoblin', got {enemies}"

    def test_multiple_enemies_extraction(self, game_screen_multiple_enemies):
        """Test extraction of multiple enemies from screen (endoplasm and kobold)."""
        bot = DCSSBot()
        
        # Should extract both enemies
        enemies = bot._extract_all_enemies_from_tui(game_screen_multiple_enemies)
        
        assert len(enemies) >= 2, f"Expected at least 2 enemies, got {len(enemies)}: {enemies}"
        assert "endoplasm" in enemies, "Expected 'endoplasm' in monster list"
        assert "kobold" in enemies, "Expected 'kobold' in monster list"

    def test_different_run_enemy_extraction(self, game_screen_different_run):
        """Test extraction of enemy from different game run (quokka)."""
        bot = DCSSBot()
        
        # Should extract quokka
        enemies = bot._extract_all_enemies_from_tui(game_screen_different_run)
        
        assert len(enemies) > 0, "Should find enemies in TUI section"
        assert "quokka" in enemies, f"Expected 'quokka', got {enemies}"

    def test_enemy_name_from_single_screen(self, game_screen_single_enemy):
        """Test that extract_enemy_name returns correct name."""
        bot = DCSSBot()
        
        # Should extract hobgoblin
        name = bot._extract_enemy_name(game_screen_single_enemy)
        
        assert name == "hobgoblin", f"Expected 'hobgoblin', got '{name}'"

    def test_enemy_name_from_multiple_screen(self, game_screen_multiple_enemies):
        """Test that extract_enemy_name returns first enemy from multiple."""
        bot = DCSSBot()
        
        # Should extract one of the enemies
        name = bot._extract_enemy_name(game_screen_multiple_enemies)
        
        assert name in ["endoplasm", "kobold"], f"Expected endoplasm or kobold, got '{name}'"

    def test_enemy_name_from_different_run(self, game_screen_different_run):
        """Test extraction from different game run."""
        bot = DCSSBot()
        
        # Should extract quokka
        name = bot._extract_enemy_name(game_screen_different_run)
        
        assert name == "quokka", f"Expected 'quokka', got '{name}'"


class TestScreenParsing:
    """Test parsing of screen state from real game output."""

    def test_health_parsing_single_enemy(self, game_screen_single_enemy):
        """Test health value parsing from real screen."""
        bot = DCSSBot()
        bot.parser.parse_output(game_screen_single_enemy)
        
        assert bot.parser.state.health > 0, "Should detect player health"
        assert bot.parser.state.max_health > 0, "Should detect max health"
        assert bot.parser.state.health <= bot.parser.state.max_health, "Health should be <= max health"

    def test_health_parsing_multiple_enemies(self, game_screen_multiple_enemies):
        """Test health parsing with multiple enemies visible."""
        bot = DCSSBot()
        bot.parser.parse_output(game_screen_multiple_enemies)
        
        assert bot.parser.state.health > 0
        assert bot.parser.state.max_health > 0

    def test_game_ready_detection(self, game_screen_single_enemy):
        """Test that game is detected as ready on real screen."""
        bot = DCSSBot()
        
        is_ready = bot.parser.is_game_ready(game_screen_single_enemy)
        
        assert is_ready is True, "Game should be detected as ready"

    def test_tui_monsters_parsing_consistency(self, game_screen_single_enemy, game_screen_multiple_enemies):
        """Test that TUI parsing is consistent across screens."""
        bot = DCSSBot()
        
        # Both should successfully extract enemies
        enemies1 = bot._extract_all_enemies_from_tui(game_screen_single_enemy)
        enemies2 = bot._extract_all_enemies_from_tui(game_screen_multiple_enemies)
        
        assert len(enemies1) > 0, "Should find enemies in single enemy screen"
        assert len(enemies2) > 0, "Should find enemies in multiple enemies screen"
        # Single should have fewer enemies than multiple
        assert len(enemies1) <= len(enemies2), "Single enemy screen should have <= enemies than multiple screen"

    def test_enemy_extraction_no_false_positives(self, game_screens):
        """Test that extraction doesn't produce false positives."""
        bot = DCSSBot()
        
        for screen_name, screen_content in game_screens.items():
            enemies = bot._extract_all_enemies_from_tui(screen_content)
            
            # All enemies should be actual creature names, not UI elements
            invalid_names = [e for e in enemies if e in ['place', 'noise', 'time', 'ac', 'ev', 'sh', 'xl', 'next']]
            assert len(invalid_names) == 0, f"Found invalid enemy names in {screen_name}: {invalid_names}"

    def test_multiword_enemy_names(self):
        """Test that multi-word enemy names like 'ball python' are captured correctly."""
        import re
        bot = DCSSBot()
        
        # Simulate TUI monsters section with multi-word enemy names and status info
        test_line = 'S   ball python (constriction, asleep)                 │'
        
        # Extract using the actual regex pattern from _extract_all_enemies_from_tui
        pattern = r'([a-zA-Z])\s{3,}([\w\s]+?)(?:\s*\(|\s*(?:│|$))'
        match = re.search(pattern, test_line)
        
        assert match is not None, "Should find multi-word creature in TUI monsters section"
        creature_name = match.group(2).strip()
        assert creature_name == "ball python", f"Expected 'ball python', got '{creature_name}'"

    def test_grouped_lowercase_creature_symbols(self, game_screen_grouped_lowercase_goblins):
        """Test extraction of grouped creatures with lowercase symbols (gg  2 goblins)."""
        bot = DCSSBot()
        
        # Should extract goblins from grouped lowercase format
        enemies = bot._extract_all_enemies_from_tui(game_screen_grouped_lowercase_goblins)
        
        assert len(enemies) > 0, "Should find enemies in grouped lowercase goblin screen"
        assert "goblins" in enemies, f"Expected 'goblins' in grouped lowercase format, got {enemies}"

    def test_detect_enemy_with_grouped_lowercase_goblins(self, game_screen_grouped_lowercase_goblins):
        """Test that enemy detection works with grouped lowercase creature symbols."""
        bot = DCSSBot()
        
        # Should detect that there are enemies
        detected, enemy_name = bot._detect_enemy_in_range(game_screen_grouped_lowercase_goblins)
        
        assert detected is True, "Should detect enemy with grouped lowercase goblins"
        assert enemy_name == "goblins", f"Expected enemy name 'goblins', got '{enemy_name}'"
    def test_message_artifacts_not_detected_as_enemies(self):
        """Test that message artifacts like 'Found 19 sling bullets' are not detected as monsters."""
        bot = DCSSBot()
        
        # Message lines containing "Found" should not be parsed as creature entries
        test_screen = """
│_Found 19 sling bullets.
│_No target in view!
        """
        
        enemies = bot._extract_all_enemies_from_tui(test_screen)
        
        # Should not detect "sling" as an enemy
        assert "sling" not in enemies, f"Should not detect 'sling' from message artifact, got {enemies}"
        assert len(enemies) == 0, f"Should detect no enemies in message-only screen, got {enemies}"

    def test_item_pickup_messages_dont_trigger_combat(self):
        """Test that item pickup messages are not confused with enemy presence."""
        bot = DCSSBot()
        
        # When player picks up items after killing a creature, the message may contain
        # patterns that look like "Found X item_name" - this should not trigger combat
        test_cases = [
            ("│_Found 19 sling bullets.", "sling"),
            ("│_Found 8 gold pieces.", "gold"),
            ("│_Found a potion of healing.", "potion"),
        ]
        
        for message_line, item_name in test_cases:
            enemies = bot._extract_all_enemies_from_tui(message_line)
            assert item_name not in enemies, f"Item '{item_name}' incorrectly detected as enemy in: {message_line}"

    def test_inventory_gold_message_not_detected_as_enemy(self):
        """Test that 'you have X gold' inventory messages are not detected as enemies.
        
        Regression test for issue where bot run detected "have (9x) -> gold" as enemy
        and attempted autofight. The word "have" must be in invalid_symbols to prevent
        this pattern from matching as a grouped creature entry.
        """
        bot = DCSSBot()
        
        # Messages showing player's gold should not be confused with combat
        test_cases = [
            "You have 9 gold pieces.",
            "│_You have 150 gold.",
            "│_Currently have 42 gold pieces",
        ]
        
        for message in test_cases:
            enemies = bot._extract_all_enemies_from_tui(message)
            assert "gold" not in enemies, f"Gold item incorrectly detected as enemy from: {message}"
            assert len(enemies) == 0, f"Expected no enemies in inventory message, got {enemies}"