"""Tests for inventory parsing and potion identification system."""

import pytest
from src.game_state import GameStateParser, InventoryItem, GameState


class TestInventoryParsing:
    """Test inventory screen parsing."""
    
    def test_parse_empty_inventory(self):
        """Test parsing an empty inventory screen."""
        parser = GameStateParser()
        screen = "You aren't carrying anything.\n"
        
        items = parser.parse_inventory_screen(screen)
        assert len(items) == 0
        assert len(parser.state.inventory_items) == 0
    
    def test_parse_simple_inventory(self):
        """Test parsing inventory with basic items."""
        parser = GameStateParser()
        screen = """
a - a +0 war axe
b - a ring of protection
c - 42 gold pieces
"""
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 3
        assert items['a'].name == 'a +0 war axe'
        assert items['a'].item_type == 'weapon'
        assert items['a'].identified == True
        
        assert items['b'].name == 'a ring of protection'
        assert items['b'].item_type == 'armor'
        
        assert items['c'].name == '42 gold pieces'
        assert items['c'].item_type == 'gold'
        assert items['c'].quantity == 42
    
    def test_parse_identified_potion(self):
        """Test parsing an identified potion."""
        parser = GameStateParser()
        screen = "a - a purple potion of healing\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].item_type == 'potion'
        assert items['a'].identified == True
        assert items['a'].color == 'purple'
    
    def test_parse_unidentified_potion(self):
        """Test parsing an unidentified potion."""
        parser = GameStateParser()
        screen = "a - a red potion (unknown)\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].item_type == 'potion'
        assert items['a'].identified == False
        assert items['a'].color == 'red'
        # Should be tracked in untested_potions
        assert 'a' in parser.state.untested_potions
        assert parser.state.untested_potions['a'] == 'red'
    
    def test_parse_multiple_potions_mixed(self):
        """Test parsing multiple potions, some identified and some not."""
        parser = GameStateParser()
        screen = """
a - a purple potion of healing
b - a blue potion (unknown)
c - a green potion
d - a cyan potion (unknown)
"""
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 4
        assert items['a'].identified == True
        assert items['b'].identified == False
        assert items['c'].identified == True
        assert items['d'].identified == False
        
        # Check untested potions
        untested = parser.state.untested_potions
        assert len(untested) == 2
        assert 'b' in untested
        assert 'd' in untested
        assert untested['b'] == 'blue'
        assert untested['d'] == 'cyan'
    
    def test_parse_scrolls(self):
        """Test parsing scrolls."""
        parser = GameStateParser()
        screen = """
a - a scroll of identify
b - a scroll of teleportation (unknown)
"""
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 2
        assert items['a'].item_type == 'scroll'
        assert items['a'].identified == True
        assert items['b'].item_type == 'scroll'
        assert items['b'].identified == False
    
    def test_parse_with_ansi_codes(self):
        """Test parsing inventory with ANSI color codes."""
        parser = GameStateParser()
        screen = "\x1b[32ma - a +0 war axe\x1b[0m\n\x1b[35mb - a purple potion (unknown)\x1b[0m\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 2
        assert 'a' in items
        assert 'b' in items
        assert items['b'].color == 'purple'


class TestGroundItemsParsing:
    """Test parsing items on the ground."""
    
    def test_you_see_here_single_item(self):
        """Test parsing 'You see here' message."""
        parser = GameStateParser()
        screen = "You see here 10 gold pieces."
        
        items = parser.parse_ground_items(screen)
        
        assert len(items) == 1
        assert items[0][0] == '10 gold pieces'
        assert items[0][1] == 10
    
    def test_you_see_here_multiple_items(self):
        """Test parsing multiple ground items."""
        parser = GameStateParser()
        screen = """
You see here a purple potion.
You see here a dagger.
"""
        items = parser.parse_ground_items(screen)
        
        assert len(items) == 2
        assert 'purple potion' in items[0][0]
        assert 'dagger' in items[1][0]
    
    def test_things_that_are_here_format(self):
        """Test parsing 'Things that are here:' section."""
        parser = GameStateParser()
        screen = """Things that are here:
a - 10 gold pieces
b - a purple potion
c - a +0 dagger
"""
        items = parser.parse_ground_items(screen)
        
        assert len(items) >= 1
        # Should find at least the gold and potion
        assert any('gold' in item[0].lower() for item in items)
    
    def test_no_items_on_ground(self):
        """Test when there are no items on the ground."""
        parser = GameStateParser()
        screen = "Nothing to see here."
        
        items = parser.parse_ground_items(screen)
        
        assert len(items) == 0


class TestInventoryItemDataclass:
    """Test InventoryItem dataclass."""
    
    def test_inventory_item_creation(self):
        """Test creating an InventoryItem."""
        item = InventoryItem(
            slot='a',
            name='a +0 war axe',
            quantity=1,
            identified=True,
            color=None,
            item_type='weapon'
        )
        
        assert item.slot == 'a'
        assert item.name == 'a +0 war axe'
        assert item.quantity == 1
        assert item.identified == True
        assert item.item_type == 'weapon'
    
    def test_potion_item(self):
        """Test creating a potion InventoryItem."""
        item = InventoryItem(
            slot='b',
            name='a purple potion (unknown)',
            quantity=1,
            identified=False,
            color='purple',
            item_type='potion'
        )
        
        assert item.item_type == 'potion'
        assert item.color == 'purple'
        assert item.identified == False
    
    def test_gold_item(self):
        """Test creating a gold InventoryItem."""
        item = InventoryItem(
            slot='c',
            name='42 gold pieces',
            quantity=42,
            identified=True,
            color=None,
            item_type='gold'
        )
        
        assert item.item_type == 'gold'
        assert item.quantity == 42


class TestGameStateInventoryTracking:
    """Test game state inventory tracking."""
    
    def test_gamestate_has_inventory_fields(self):
        """Test that GameState has inventory tracking fields."""
        state = GameState()
        
        assert hasattr(state, 'inventory_items')
        assert hasattr(state, 'identified_potions')
        assert hasattr(state, 'untested_potions')
        assert hasattr(state, 'items_on_ground')
        
        assert isinstance(state.inventory_items, dict)
        assert isinstance(state.identified_potions, dict)
        assert isinstance(state.untested_potions, dict)
        assert isinstance(state.items_on_ground, list)
    
    def test_gamestate_initial_state(self):
        """Test that GameState initializes with empty inventory."""
        state = GameState()
        
        assert len(state.inventory_items) == 0
        assert len(state.identified_potions) == 0
        assert len(state.untested_potions) == 0
        assert len(state.items_on_ground) == 0


class TestPotionColorVariation:
    """Test parsing potions with various colors."""
    
    @pytest.mark.parametrize("color", [
        "purple", "red", "blue", "green", "yellow", "cyan", 
        "magenta", "brown", "gray", "white", "black", 
        "orange", "golden", "silver", "pink", "violet", "indigo", "turquoise"
    ])
    def test_potion_color_detection(self, color):
        """Test that all potion colors are detected."""
        parser = GameStateParser()
        screen = f"a - a {color} potion (unknown)\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].color == color
        assert items['a'].item_type == 'potion'
        assert items['a'].identified == False


class TestComplexInventoryScenario:
    """Test complex inventory scenarios with mixed items."""
    
    def test_full_inventory_with_all_types(self):
        """Test parsing a full inventory with all item types."""
        parser = GameStateParser()
        screen = """
a - a +1 war axe
b - a +2 leather armour
c - a ring of fire resistance
d - a purple potion of healing
e - a red potion (unknown)
f - a blue potion (unknown)
g - a scroll of identify
h - a scroll of teleportation (unknown)
i - 150 gold pieces
"""
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 9
        
        # Check weapon
        assert items['a'].item_type == 'weapon'
        # Check armor
        assert items['b'].item_type == 'armor'
        # Check identified potion
        assert items['d'].item_type == 'potion'
        assert items['d'].identified == True
        # Check unidentified potions
        assert items['e'].identified == False
        assert items['f'].identified == False
        # Check scrolls
        assert items['g'].item_type == 'scroll'
        assert items['h'].item_type == 'scroll'
        # Check gold
        assert items['i'].item_type == 'gold'
        assert items['i'].quantity == 150
        
        # Check untested potions tracking
        untested = parser.state.untested_potions
        assert len(untested) == 2
        assert untested['e'] == 'red'
        assert untested['f'] == 'blue'
