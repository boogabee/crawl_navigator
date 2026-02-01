"""Tests for equipment system: AC parsing, equipment tracking, and equipment comparison."""

import pytest
from src.game_state import GameStateParser, InventoryItem, GameState


class TestACValueParsing:
    """Test AC value parsing from armor items."""
    
    def test_parse_positive_ac_armor(self):
        """Test parsing armor with positive AC (protection)."""
        parser = GameStateParser()
        screen = "a - a +2 leather armour\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].item_type == 'armor'
        # +2 protection means -2 AC value (lower is better)
        assert items['a'].ac_value == -2
    
    def test_parse_negative_ac_armor(self):
        """Test parsing armor with negative AC (penalty)."""
        parser = GameStateParser()
        screen = "a - a -1 scale mail\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].item_type == 'armor'
        # -1 penalty means +1 AC value (worse)
        assert items['a'].ac_value == 1
    
    def test_parse_zero_ac_armor(self):
        """Test parsing armor with no AC modifier."""
        parser = GameStateParser()
        screen = "a - a +0 leather armour\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].ac_value == 0
    
    def test_parse_high_ac_armor(self):
        """Test parsing armor with high protection."""
        parser = GameStateParser()
        screen = "a - a +5 chain mail\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].ac_value == -5  # 5 points of protection
    
    def test_parse_ring_ac_value(self):
        """Test parsing rings with AC modifiers."""
        parser = GameStateParser()
        screen = "a - a +1 ring of protection\n"
        
        items = parser.parse_inventory_screen(screen)
        
        assert len(items) == 1
        assert items['a'].item_type == 'armor'
        assert items['a'].ac_value == -1


class TestEquipmentSlotDetection:
    """Test detection of equipment slots from armor items."""
    
    def test_body_armor_detection(self):
        """Test detection of body armor (robe, armor, tunic)."""
        parser = GameStateParser()
        screen = """
a - a +2 leather armour
b - a +1 robe
c - a +0 scale mail
"""
        items = parser.parse_inventory_screen(screen)
        
        assert items['a'].equipment_slot == 'body'
        assert items['b'].equipment_slot == 'body'
        assert items['c'].equipment_slot == 'body'
    
    def test_hand_armor_detection(self):
        """Test detection of hand armor (gloves, gauntlets)."""
        parser = GameStateParser()
        screen = """
a - a +1 gloves
b - a +0 gauntlets
"""
        items = parser.parse_inventory_screen(screen)
        
        assert items['a'].equipment_slot == 'hands'
        assert items['b'].equipment_slot == 'hands'
    
    def test_foot_armor_detection(self):
        """Test detection of foot armor (boots, sandals)."""
        parser = GameStateParser()
        screen = """
a - a +1 boots
b - a +0 sandals
"""
        items = parser.parse_inventory_screen(screen)
        
        assert items['a'].equipment_slot == 'feet'
        assert items['b'].equipment_slot == 'feet'
    
    def test_head_armor_detection(self):
        """Test detection of head armor (helmet, crown)."""
        parser = GameStateParser()
        screen = """
a - a +1 helmet
b - a +0 circlet
c - a +1 crown
"""
        items = parser.parse_inventory_screen(screen)
        
        assert items['a'].equipment_slot == 'head'
        assert items['b'].equipment_slot == 'head'
        assert items['c'].equipment_slot == 'head'
    
    def test_neck_jewelry_detection(self):
        """Test detection of neck jewelry (rings, amulets, necklaces)."""
        parser = GameStateParser()
        screen = """
a - a +1 ring of protection
b - a +0 amulet of life saving
c - a +1 necklace
"""
        items = parser.parse_inventory_screen(screen)
        
        assert items['a'].equipment_slot == 'neck'
        assert items['b'].equipment_slot == 'neck'
        assert items['c'].equipment_slot == 'neck'


class TestEquipmentTracking:
    """Test equipment state tracking."""
    
    def test_gamestate_has_equipment_fields(self):
        """Test that GameState has equipment tracking fields."""
        state = GameState()
        
        assert hasattr(state, 'equipped_items')
        assert hasattr(state, 'current_ac')
        assert isinstance(state.equipped_items, dict)
        assert isinstance(state.current_ac, int)
    
    def test_equipped_items_default_state(self):
        """Test that GameState initializes with no equipped items."""
        state = GameState()
        
        assert len(state.equipped_items) == 0
        assert state.current_ac == 10  # Default AC
    
    def test_mark_item_as_equipped(self):
        """Test marking an item as equipped."""
        item = InventoryItem(
            slot='a',
            name='a +2 leather armour',
            item_type='armor',
            ac_value=-2,
            is_equipped=True,
            equipment_slot='body'
        )
        
        assert item.is_equipped == True
        assert item.equipment_slot == 'body'
    
    def test_get_equipped_ac_total_single_item(self):
        """Test calculating total AC with a single equipped item."""
        parser = GameStateParser()
        
        # Manually set up equipped items
        item = InventoryItem(
            slot='a',
            name='a +2 leather armour',
            item_type='armor',
            ac_value=-2,
            is_equipped=True,
            equipment_slot='body'
        )
        parser.state.equipped_items['body'] = item
        
        total_ac = parser.get_equipped_ac_total()
        assert total_ac == -2
    
    def test_get_equipped_ac_total_multiple_items(self):
        """Test calculating total AC with multiple equipped items."""
        parser = GameStateParser()
        
        # Set up multiple equipped items
        body_item = InventoryItem(
            slot='a',
            name='a +2 leather armour',
            item_type='armor',
            ac_value=-2,
            is_equipped=True,
            equipment_slot='body'
        )
        head_item = InventoryItem(
            slot='b',
            name='a +1 helmet',
            item_type='armor',
            ac_value=-1,
            is_equipped=True,
            equipment_slot='head'
        )
        feet_item = InventoryItem(
            slot='c',
            name='a +1 boots',
            item_type='armor',
            ac_value=-1,
            is_equipped=True,
            equipment_slot='feet'
        )
        
        parser.state.equipped_items['body'] = body_item
        parser.state.equipped_items['head'] = head_item
        parser.state.equipped_items['feet'] = feet_item
        
        total_ac = parser.get_equipped_ac_total()
        # Total protection: 2 + 1 + 1 = 4, so AC = -4
        assert total_ac == -4


class TestFindBetterArmor:
    """Test finding better armor to equip."""
    
    def test_find_better_armor_in_inventory(self):
        """Test finding better armor than currently equipped."""
        parser = GameStateParser()
        
        # Set up current equipped item
        current = InventoryItem(
            slot='a',
            name='a +1 leather armour',
            item_type='armor',
            ac_value=-1,
            is_equipped=True,
            equipment_slot='body'
        )
        parser.state.equipped_items['body'] = current
        
        # Add better armor to inventory
        better = InventoryItem(
            slot='b',
            name='a +3 chain mail',
            item_type='armor',
            ac_value=-3,
            is_equipped=False,
            equipment_slot='body'
        )
        parser.state.inventory_items['b'] = better
        
        # Should find the better armor
        result = parser.find_better_armor()
        
        assert result is not None
        slot, item = result
        assert slot == 'b'
        assert item.ac_value == -3
    
    def test_find_better_armor_skip_equipped(self):
        """Test that find_better_armor skips already equipped items."""
        parser = GameStateParser()
        
        # Set up current equipped item
        current = InventoryItem(
            slot='a',
            name='a +1 leather armour',
            item_type='armor',
            ac_value=-1,
            is_equipped=True,
            equipment_slot='body'
        )
        parser.state.equipped_items['body'] = current
        
        # Add an equipped item to inventory (should skip this)
        equipped_item = InventoryItem(
            slot='b',
            name='a +5 plate mail',
            item_type='armor',
            ac_value=-5,
            is_equipped=True,  # Already equipped!
            equipment_slot='body'
        )
        parser.state.inventory_items['b'] = equipped_item
        
        # Should return None (skip equipped items)
        result = parser.find_better_armor()
        
        assert result is None
    
    def test_find_better_armor_for_empty_slot(self):
        """Test finding armor when a slot is completely empty."""
        parser = GameStateParser()
        
        # No equipped items yet (empty head slot)
        # Add armor to inventory for head slot
        item = InventoryItem(
            slot='a',
            name='a +2 helmet',
            item_type='armor',
            ac_value=-2,
            is_equipped=False,
            equipment_slot='head'
        )
        parser.state.inventory_items['a'] = item
        
        # Should find this armor for the empty slot
        result = parser.find_better_armor()
        
        assert result is not None
        slot, item = result
        assert slot == 'a'
        assert item.equipment_slot == 'head'
    
    def test_find_better_armor_no_improvement(self):
        """Test that find_better_armor returns None if no improvement available."""
        parser = GameStateParser()
        
        # Set up good equipped item
        current = InventoryItem(
            slot='a',
            name='a +5 chain mail',
            item_type='armor',
            ac_value=-5,
            is_equipped=True,
            equipment_slot='body'
        )
        parser.state.equipped_items['body'] = current
        
        # Add worse armor to inventory
        worse = InventoryItem(
            slot='b',
            name='a +1 leather armour',
            item_type='armor',
            ac_value=-1,
            is_equipped=False,
            equipment_slot='body'
        )
        parser.state.inventory_items['b'] = worse
        
        # Should return None (no improvement)
        result = parser.find_better_armor()
        
        assert result is None
    
    def test_find_better_armor_multiple_slots(self):
        """Test finding best improvement among multiple slots."""
        parser = GameStateParser()
        
        # Set up some equipped items
        body_eq = InventoryItem(
            slot='a',
            name='a +1 leather armour',
            item_type='armor',
            ac_value=-1,
            is_equipped=True,
            equipment_slot='body'
        )
        head_eq = InventoryItem(
            slot='b',
            name='a +1 helmet',
            item_type='armor',
            ac_value=-1,
            is_equipped=True,
            equipment_slot='head'
        )
        parser.state.equipped_items['body'] = body_eq
        parser.state.equipped_items['head'] = head_eq
        
        # Add multiple improvements to inventory
        body_better = InventoryItem(
            slot='c',
            name='a +2 chain mail',
            item_type='armor',
            ac_value=-2,
            is_equipped=False,
            equipment_slot='body'
        )
        head_better = InventoryItem(
            slot='d',
            name='a +4 crown',
            item_type='armor',
            ac_value=-4,
            is_equipped=False,
            equipment_slot='head'
        )
        parser.state.inventory_items['c'] = body_better
        parser.state.inventory_items['d'] = head_better
        
        # Should find the best improvement (head: +3 improvement vs body: +1 improvement)
        result = parser.find_better_armor()
        
        assert result is not None
        slot, item = result
        assert slot == 'd'  # Should pick head improvement (more significant)
        assert item.ac_value == -4


class TestEquipmentComparisonLogic:
    """Test comparison logic for equipment decisions."""
    
    def test_armor_only_better_if_significant(self):
        """Test that equipment upgrades require significant improvement."""
        parser = GameStateParser()
        
        # Current equipped
        current = InventoryItem(
            slot='a',
            name='a +2 leather armour',
            item_type='armor',
            ac_value=-2,
            is_equipped=True,
            equipment_slot='body'
        )
        parser.state.equipped_items['body'] = current
        
        # Minor improvement (only +0.5) should not trigger equip
        minor = InventoryItem(
            slot='b',
            name='a +2 robe',  # Same AC, just different item
            item_type='armor',
            ac_value=-2,
            is_equipped=False,
            equipment_slot='body'
        )
        parser.state.inventory_items['b'] = minor
        
        # No improvement expected for equal AC
        result = parser.find_better_armor()
        assert result is None
    
    def test_armor_by_slot_independence(self):
        """Test that armor in different slots are compared independently."""
        parser = GameStateParser()
        
        # One equipped in body slot
        body = InventoryItem(
            slot='a',
            name='a +5 plate mail',
            item_type='armor',
            ac_value=-5,
            is_equipped=True,
            equipment_slot='body'
        )
        parser.state.equipped_items['body'] = body
        
        # Add items for different slots
        head = InventoryItem(
            slot='b',
            name='a +1 helmet',
            item_type='armor',
            ac_value=-1,
            is_equipped=False,
            equipment_slot='head'
        )
        feet = InventoryItem(
            slot='c',
            name='a +1 boots',
            item_type='armor',
            ac_value=-1,
            is_equipped=False,
            equipment_slot='feet'
        )
        parser.state.inventory_items['b'] = head
        parser.state.inventory_items['c'] = feet
        
        # Should find improvement in head or feet (body slot already has best armor)
        result = parser.find_better_armor()
        
        assert result is not None
        slot, item = result
        assert slot in ('b', 'c')  # Should be head or feet
        assert item.equipment_slot in ('head', 'feet')
